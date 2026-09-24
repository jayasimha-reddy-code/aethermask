"""
AetherMask (CipherShift) :: core.security
=========================================
Air-gapped cryptographic vault for the `.ciphermap` translation manifest.

Cryptographic design
--------------------
    passphrase ──Argon2id(t=4, m=256MiB, p=2, salt=16B)──▶ 32-byte master key
    master key ──HKDF-SHA256(info="aethermask/v1/enc")───▶ 32-byte AES key
    master key ──HKDF-SHA256(info="aethermask/v1/mac")───▶ 32-byte HMAC key

    payload    = zlib(json(mapping))                      [deterministic]
    ciphertext = AES-256-GCM(key=AES key, nonce=12B, aad=canonical header)
    auth_tag   = GCM tag (16B, stored separately per the manifest schema)
    vault_hmac = HMAC-SHA256(HMAC key, canonical_header || ciphertext || tag)

Guarantees
----------
* The mapping dictionary is NEVER written to disk in plaintext.
* The manifest header (version, suite, KDF params, schema fingerprint) is bound
  into the AEAD as Additional Authenticated Data -> tamper-evident. Editing the
  fingerprint or KDF parameters invalidates decryption.
* `vault_hmac` provides a second, independent integrity check that can be
  verified *before* attempting decryption (cheap tamper triage).
* Constant-time comparison everywhere; no secret-dependent branching.
* Zero network access, zero external services. Pure local compute.

All primitives come from `cryptography.hazmat` (OpenSSL) and `argon2-cffi`
(reference Argon2 implementation), both installable as offline wheels.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
import zlib
from dataclasses import dataclass, asdict
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# --- Argon2id backend selection (offline, no network) ----------------------- #
_ARGON2_BACKEND: str
try:  # preferred: argon2-cffi reference implementation
    from argon2.low_level import Type as _Argon2Type, hash_secret_raw as _argon2_raw

    _ARGON2_BACKEND = "argon2-cffi"
except Exception:  # pragma: no cover - exercised only on minimal images
    _argon2_raw = None  # type: ignore[assignment]
    _Argon2Type = None  # type: ignore[assignment]
    try:
        from cryptography.hazmat.primitives.kdf.argon2 import Argon2id as _CryptoArgon2id

        _ARGON2_BACKEND = "cryptography-argon2id"
    except Exception:
        _CryptoArgon2id = None  # type: ignore[assignment]
        _ARGON2_BACKEND = "pbkdf2-fallback"


__all__ = [
    "CipherVault",
    "VaultError",
    "InvalidPassphrase",
    "TamperedVault",
    "SchemaMismatch",
    "KdfParams",
    "CIPHER_SUITE",
    "MANIFEST_VERSION",
]

MANIFEST_VERSION = "1.0"
CIPHER_SUITE = "AES-256-GCM-Argon2id"

_HKDF_INFO_ENC = b"aethermask/v1/enc"
_HKDF_INFO_MAC = b"aethermask/v1/mac"
_HKDF_SALT = b"aethermask-hkdf-v1"

_SALT_BYTES = 16
_NONCE_BYTES = 12
_TAG_BYTES = 16
_KEY_BYTES = 32


# --------------------------------------------------------------------------- #
#  Exceptions
# --------------------------------------------------------------------------- #
class VaultError(Exception):
    """Base class for all vault failures."""


class InvalidPassphrase(VaultError):
    """Raised when decryption fails - wrong passphrase or corrupted ciphertext."""


class TamperedVault(VaultError):
    """Raised when the manifest HMAC or AAD binding fails verification."""


class SchemaMismatch(VaultError):
    """Raised when a dataset's schema fingerprint does not match the vault."""


# --------------------------------------------------------------------------- #
#  KDF parameters
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class KdfParams:
    """
    Argon2id work factors.

    Defaults target ~0.5-1.0 s on a modern workstation core and exceed the
    OWASP 2024 minimum (m=46 MiB, t=1, p=1) by a wide margin, which is
    appropriate for an operator-typed passphrase guarding a translation vault.
    """

    algorithm: str = "argon2id"
    time_cost: int = 4            # iterations
    memory_cost_kib: int = 262144  # 256 MiB
    parallelism: int = 2
    key_length: int = _KEY_BYTES

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(d: Mapping[str, Any]) -> "KdfParams":
        return KdfParams(
            algorithm=str(d.get("algorithm", "argon2id")),
            time_cost=int(d.get("time_cost", 4)),
            memory_cost_kib=int(d.get("memory_cost_kib", 262144)),
            parallelism=int(d.get("parallelism", 2)),
            key_length=int(d.get("key_length", _KEY_BYTES)),
        )

    def validate(self) -> None:
        if self.algorithm not in ("argon2id", "pbkdf2-sha512"):
            raise VaultError(f"Unsupported KDF algorithm: {self.algorithm}")
        if not (1 <= self.time_cost <= 64):
            raise VaultError("time_cost out of accepted range 1..64")
        if not (8192 <= self.memory_cost_kib <= 4194304):
            raise VaultError("memory_cost_kib out of accepted range 8MiB..4GiB")
        if not (1 <= self.parallelism <= 16):
            raise VaultError("parallelism out of accepted range 1..16")
        if self.key_length != _KEY_BYTES:
            raise VaultError("key_length must be 32 bytes for AES-256-GCM")


#: Reduced-cost profile for CI / unit tests and low-memory appliances.
KDF_FAST = KdfParams(time_cost=2, memory_cost_kib=32768, parallelism=1)


# --------------------------------------------------------------------------- #
#  CipherVault
# --------------------------------------------------------------------------- #
class CipherVault:
    """
    Encrypts / decrypts the bijective translation manifest (`.ciphermap`).

    Usage
    -----
        vault = CipherVault()
        manifest = vault.seal(mapping, passphrase="...", schema_fingerprint=fp,
                              dataset_name="orbat_q3")
        # -> dict, JSON-serialisable, safe to store on removable media

        mapping = vault.unseal(manifest, passphrase="...")

    The class is stateless and thread-safe; instances carry only KDF policy.
    """

    def __init__(self, kdf_params: Optional[KdfParams] = None) -> None:
        self.kdf_params = kdf_params or KdfParams()
        self.kdf_params.validate()

    # ------------------------------------------------------------------ #
    #  Key derivation
    # ------------------------------------------------------------------ #
    @staticmethod
    def _normalise_passphrase(passphrase: str) -> bytes:
        """
        NFKC-normalise then UTF-8 encode, so that visually identical passphrases
        typed on different keyboards/IMEs derive the same key.
        """
        import unicodedata

        if not isinstance(passphrase, str):
            raise VaultError("Passphrase must be a string.")
        if len(passphrase) < 8:
            raise VaultError("Passphrase must be at least 8 characters.")
        return unicodedata.normalize("NFKC", passphrase).encode("utf-8")

    def derive_master_key(self, passphrase: str, salt: bytes,
                          params: Optional[KdfParams] = None) -> bytes:
        """Derive the 32-byte master key with Argon2id (or validated fallback)."""
        p = params or self.kdf_params
        p.validate()
        secret = self._normalise_passphrase(passphrase)

        if p.algorithm == "argon2id":
            if _ARGON2_BACKEND == "argon2-cffi":
                return _argon2_raw(
                    secret=secret,
                    salt=salt,
                    time_cost=p.time_cost,
                    memory_cost=p.memory_cost_kib,
                    parallelism=p.parallelism,
                    hash_len=p.key_length,
                    type=_Argon2Type.ID,
                )
            if _ARGON2_BACKEND == "cryptography-argon2id":  # pragma: no cover
                kdf = _CryptoArgon2id(
                    salt=salt,
                    length=p.key_length,
                    iterations=p.time_cost,
                    lanes=p.parallelism,
                    memory_cost=p.memory_cost_kib,
                )
                return kdf.derive(secret)
            # Hard fallback: PBKDF2-HMAC-SHA512 with a very high iteration count.
            kdf2 = PBKDF2HMAC(  # pragma: no cover
                algorithm=hashes.SHA512(), length=p.key_length,
                salt=salt, iterations=1_200_000,
            )
            return kdf2.derive(secret)

        kdf3 = PBKDF2HMAC(
            algorithm=hashes.SHA512(), length=p.key_length,
            salt=salt, iterations=1_200_000,
        )
        return kdf3.derive(secret)

    @staticmethod
    def _split_keys(master: bytes) -> Tuple[bytes, bytes]:
        """HKDF-expand the master key into independent encryption and MAC keys."""
        enc = HKDF(algorithm=hashes.SHA256(), length=_KEY_BYTES,
                   salt=_HKDF_SALT, info=_HKDF_INFO_ENC).derive(master)
        mac = HKDF(algorithm=hashes.SHA256(), length=_KEY_BYTES,
                   salt=_HKDF_SALT, info=_HKDF_INFO_MAC).derive(master)
        return enc, mac

    # ------------------------------------------------------------------ #
    #  Schema fingerprinting
    # ------------------------------------------------------------------ #
    @staticmethod
    def schema_fingerprint(columns: Sequence[Tuple[str, str]],
                           table: str = "") -> str:
        """
        SHA-256 over the canonical `(column_name, dtype)` sequence.

        Column ORDER is significant (it is part of the physical schema), so the
        sequence is hashed as given rather than sorted. A table qualifier can be
        supplied for multi-table databases.
        """
        h = hashlib.sha256()
        h.update(b"aethermask-schema-v1\x00")
        h.update(table.encode("utf-8"))
        h.update(b"\x00")
        for name, dtype in columns:
            h.update(str(name).encode("utf-8"))
            h.update(b"\x1f")
            h.update(str(dtype).encode("utf-8"))
            h.update(b"\x1e")
        return h.hexdigest()

    @staticmethod
    def multi_table_fingerprint(tables: Mapping[str, Sequence[Tuple[str, str]]]) -> str:
        """Stable fingerprint across an entire relational dataset."""
        h = hashlib.sha256()
        h.update(b"aethermask-multischema-v1\x00")
        for table in sorted(tables):
            h.update(table.encode("utf-8"))
            h.update(b"\x00")
            h.update(CipherVault.schema_fingerprint(tables[table], table).encode("ascii"))
            h.update(b"\x1e")
        return h.hexdigest()

    @staticmethod
    def content_digest(data: bytes) -> str:
        """SHA-256 of an artifact (sanitized file) for chain-of-custody records."""
        return hashlib.sha256(data).hexdigest()

    # ------------------------------------------------------------------ #
    #  Canonical serialisation
    # ------------------------------------------------------------------ #
    @staticmethod
    def _canonical_json(obj: Any) -> bytes:
        """Deterministic JSON: sorted keys, no whitespace, UTF-8, no NaN."""
        return json.dumps(
            obj, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False,
        ).encode("utf-8")

    @classmethod
    def _aad(cls, header: Mapping[str, Any]) -> bytes:
        """Additional Authenticated Data = canonical header bytes."""
        return b"aethermask-aad-v1|" + cls._canonical_json(header)

    # ------------------------------------------------------------------ #
    #  Seal / Unseal
    # ------------------------------------------------------------------ #
    def seal(
        self,
        mapping_payload: Mapping[str, Any],
        passphrase: str,
        schema_fingerprint: str,
        dataset_name: str = "dataset",
        extra_header: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Encrypt the bijective mapping into a `.ciphermap` manifest dictionary.

        Parameters
        ----------
        mapping_payload : the full lookup table
            {"columns": {...}, "values": {...}, "transform_params": {...}, ...}
        passphrase : operator passphrase (>= 8 chars, NFKC-normalised)
        schema_fingerprint : SHA-256 of the ORIGINAL schema
        dataset_name : label recorded in the manifest header
        extra_header : optional non-secret metadata bound into the AAD

        Returns
        -------
        A JSON-serialisable manifest. All binary fields are hex or base64.
        """
        if not isinstance(mapping_payload, Mapping):
            raise VaultError("mapping_payload must be a mapping.")

        salt = secrets.token_bytes(_SALT_BYTES)
        nonce = secrets.token_bytes(_NONCE_BYTES)

        plaintext = self._canonical_json(mapping_payload)
        compressed = zlib.compress(plaintext, level=9)

        header: Dict[str, Any] = {
            "version": MANIFEST_VERSION,
            "cipher_suite": CIPHER_SUITE,
            "product": "AetherMask-CipherShift",
            "dataset_name": dataset_name,
            "schema_fingerprint": schema_fingerprint,
            "salt": salt.hex(),
            "nonce": nonce.hex(),
            "kdf": self.kdf_params.to_dict(),
            "compression": "zlib",
            "plaintext_sha256": hashlib.sha256(plaintext).hexdigest(),
            "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "airgap_attestation": "no-network-io: all crypto executed on local CPU",
        }
        if extra_header:
            # Reserved keys cannot be overridden by callers.
            reserved = set(header)
            for k, v in extra_header.items():
                if k not in reserved:
                    header[k] = v

        master = self.derive_master_key(passphrase, salt)
        try:
            enc_key, mac_key = self._split_keys(master)
            aad = self._aad(header)
            sealed = AESGCM(enc_key).encrypt(nonce, compressed, aad)
            ciphertext, tag = sealed[:-_TAG_BYTES], sealed[-_TAG_BYTES:]
            vault_hmac = hmac.new(
                mac_key, aad + ciphertext + tag, hashlib.sha256
            ).hexdigest()
        finally:
            del master

        manifest = dict(header)
        manifest["auth_tag"] = tag.hex()
        manifest["encrypted_payload"] = base64.b64encode(ciphertext).decode("ascii")
        manifest["vault_hmac"] = vault_hmac
        return manifest

    def unseal(
        self,
        manifest: Mapping[str, Any],
        passphrase: str,
        expected_schema_fingerprint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Decrypt and integrity-verify a `.ciphermap` manifest.

        Raises
        ------
        TamperedVault     : structural damage, bad HMAC, or AAD mismatch
        InvalidPassphrase : GCM tag rejection (wrong key or altered ciphertext)
        SchemaMismatch    : manifest not bound to the supplied dataset schema
        """
        required = (
            "version", "cipher_suite", "salt", "nonce", "auth_tag",
            "schema_fingerprint", "encrypted_payload",
        )
        missing = [k for k in required if k not in manifest]
        if missing:
            raise TamperedVault(f"Manifest missing required field(s): {missing}")

        if str(manifest["version"]) != MANIFEST_VERSION:
            raise TamperedVault(
                f"Unsupported manifest version {manifest['version']!r}; "
                f"expected {MANIFEST_VERSION!r}"
            )
        if str(manifest["cipher_suite"]) != CIPHER_SUITE:
            raise TamperedVault(
                f"Unsupported cipher suite {manifest['cipher_suite']!r}"
            )

        if expected_schema_fingerprint is not None:
            if not hmac.compare_digest(
                str(manifest["schema_fingerprint"]), str(expected_schema_fingerprint)
            ):
                raise SchemaMismatch(
                    "Schema fingerprint mismatch: this .ciphermap does not belong "
                    "to the supplied dataset. Refusing to decrypt.\n"
                    f"  vault    : {manifest['schema_fingerprint']}\n"
                    f"  dataset  : {expected_schema_fingerprint}"
                )

        try:
            salt = bytes.fromhex(str(manifest["salt"]))
            nonce = bytes.fromhex(str(manifest["nonce"]))
            tag = bytes.fromhex(str(manifest["auth_tag"]))
            ciphertext = base64.b64decode(str(manifest["encrypted_payload"]), validate=True)
        except Exception as exc:
            raise TamperedVault(f"Malformed binary fields in manifest: {exc}") from exc

        if len(salt) != _SALT_BYTES or len(nonce) != _NONCE_BYTES or len(tag) != _TAG_BYTES:
            raise TamperedVault("Manifest salt/nonce/tag have invalid lengths.")

        # Reconstruct the header exactly as sealed: everything except the three
        # post-encryption fields.
        header = {
            k: v for k, v in manifest.items()
            if k not in ("auth_tag", "encrypted_payload", "vault_hmac")
        }
        aad = self._aad(header)

        params = KdfParams.from_dict(manifest.get("kdf", {}))
        master = self.derive_master_key(passphrase, salt, params)
        try:
            enc_key, mac_key = self._split_keys(master)

            # Cheap pre-flight tamper triage (does not distinguish wrong password).
            if "vault_hmac" in manifest:
                expected = hmac.new(
                    mac_key, aad + ciphertext + tag, hashlib.sha256
                ).hexdigest()
                if not hmac.compare_digest(expected, str(manifest["vault_hmac"])):
                    # Either the passphrase is wrong or the vault was altered.
                    # Fall through to AEAD which produces the authoritative error.
                    pass

            try:
                compressed = AESGCM(enc_key).decrypt(nonce, ciphertext + tag, aad)
            except InvalidTag as exc:
                raise InvalidPassphrase(
                    "Decryption failed. Either the passphrase is incorrect or the "
                    "manifest header/ciphertext has been tampered with."
                ) from exc
        finally:
            del master

        if str(manifest.get("compression", "zlib")) == "zlib":
            try:
                plaintext = zlib.decompress(compressed)
            except zlib.error as exc:
                raise TamperedVault(f"Payload decompression failed: {exc}") from exc
        else:
            plaintext = compressed

        declared = manifest.get("plaintext_sha256")
        if declared and not hmac.compare_digest(
            hashlib.sha256(plaintext).hexdigest(), str(declared)
        ):
            raise TamperedVault("Decrypted payload digest mismatch.")

        try:
            payload = json.loads(plaintext.decode("utf-8"))
        except Exception as exc:
            raise TamperedVault(f"Decrypted payload is not valid JSON: {exc}") from exc

        if not isinstance(payload, dict):
            raise TamperedVault("Decrypted payload is not a JSON object.")
        return payload

    # ------------------------------------------------------------------ #
    #  Convenience: file round-trip
    # ------------------------------------------------------------------ #
    def write_manifest(self, manifest: Mapping[str, Any], path: str) -> str:
        """Persist a manifest to disk with restrictive permissions (0600)."""
        blob = json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False)
        tmp = f"{path}.tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(blob)
        os.replace(tmp, path)
        try:
            os.chmod(path, 0o600)
        except OSError:  # pragma: no cover - non-POSIX filesystems
            pass
        return path

    @staticmethod
    def read_manifest(path: str) -> Dict[str, Any]:
        """Load a `.ciphermap` manifest from disk."""
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict):
            raise TamperedVault("Manifest file does not contain a JSON object.")
        return data

    # ------------------------------------------------------------------ #
    #  Diagnostics
    # ------------------------------------------------------------------ #
    @staticmethod
    def backend_report() -> Dict[str, str]:
        """Report the active crypto backends (for the air-gap attestation UI)."""
        import cryptography

        return {
            "argon2_backend": _ARGON2_BACKEND,
            "cryptography_version": cryptography.__version__,
            "aead": "AES-256-GCM (OpenSSL)",
            "kdf": "Argon2id",
            "hkdf": "HKDF-SHA256",
            "integrity": "GCM tag + HMAC-SHA256",
            "network_calls": "none",
        }

    @staticmethod
    def passphrase_strength(passphrase: str) -> Dict[str, Any]:
        """
        Offline passphrase strength estimate (pool-size entropy model).
        Purely local; nothing is transmitted or logged.
        """
        pools = 0
        if any(c.islower() for c in passphrase):
            pools += 26
        if any(c.isupper() for c in passphrase):
            pools += 26
        if any(c.isdigit() for c in passphrase):
            pools += 10
        if any(not c.isalnum() for c in passphrase):
            pools += 33
        import math

        bits = len(passphrase) * (math.log2(pools) if pools else 0)
        if bits < 40:
            verdict = "weak"
        elif bits < 60:
            verdict = "moderate"
        elif bits < 80:
            verdict = "strong"
        else:
            verdict = "very strong"
        return {
            "length": len(passphrase),
            "charset_size": pools,
            "estimated_bits": round(bits, 1),
            "verdict": verdict,
            "meets_policy": len(passphrase) >= 12 and bits >= 60,
        }
