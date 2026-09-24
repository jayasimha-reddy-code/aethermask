"""
AetherMask (CipherShift) :: core.engine
=======================================
`OfflineIsomorphicEngine` - the deterministic, bijective, statistics-preserving
semantic transformation engine.

Isomorphism contract
--------------------
For an original relation R and its masked image M = T(R):

    |R| = |M|                                     (row count)
    nulls(R.c) = nulls(M.T(c))  ∀c                (null topology)
    |distinct(R.c)| = |distinct(M.T(c))|  ∀c      (cardinality)
    P(R.c = v) = P(M.T(c) = T(v))  ∀c,v           (categorical distribution)
    R.a ⋈ R.b ≡ M.T(a) ⋈ M.T(b)                   (join/FK topology)
    numeric columns: identity, or a declared affine y = ax + b (a ≠ 0)
    T is injective on every domain it touches     (1↔1, invertible)

Because T is a *relabelling* (a graph isomorphism on the value lattice), every
count, ratio, group-by aggregate, histogram bucket, cluster assignment and
trendline computed over categorical structure is numerically identical. With
the default `numeric_mode="identity"`, all numeric aggregates are bit-identical.

Determinism
-----------
Every surrogate choice is driven by HMAC-SHA256 over a run seed plus the source
token. Same input + same seed + same profile => byte-identical output, on any
host, with no RNG state and no ordering dependence.

Everything executes on local CPU via Polars. No network. No model downloads.
"""

from __future__ import annotations

import hashlib
import hmac
import re
import string
from dataclasses import dataclass, field, asdict
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Set, Tuple

import polars as pl

from .nlp import Entity, OfflineNER, normalise_identifier, rejoin_identifier, split_identifier
from .ontology import DomainProfile, get_profile
from .profiler import SemanticRole, SensitivityProfiler, TableProfile

__all__ = [
    "OfflineIsomorphicEngine",
    "TransformConfig",
    "BijectiveMap",
    "FidelityReport",
    "FidelityError",
    "EngineError",
    "MaskResult",
    "RestoreResult",
]

ENGINE_VERSION = "1.0"


class EngineError(Exception):
    """Generic engine failure."""


class FidelityError(EngineError):
    """Raised when a statistical-isomorphism assertion fails."""


# --------------------------------------------------------------------------- #
#  Configuration
# --------------------------------------------------------------------------- #
@dataclass
class TransformConfig:
    """Operator-controlled transformation policy."""

    domain_profile: str = "defense_to_logistics"
    #: "identity"  -> numbers untouched (perfect analytical fidelity)
    #: "affine"    -> reversible y = a*x + b per column
    numeric_mode: str = "identity"
    affine_scale: float = 1.0
    affine_offset: float = 0.0
    #: Apply affine to geospatial columns only (leaves measures pristine)
    affine_geo_only: bool = True
    mask_column_names: bool = True
    mask_categoricals: bool = True
    mask_identifiers: bool = True
    mask_free_text: bool = True
    mask_table_names: bool = True
    preserve_nulls: bool = True
    #: Keep the physical format of identifiers (letter->letter, digit->digit)
    format_preserving_ids: bool = True
    #: Columns explicitly excluded from all transformation
    passthrough_columns: List[str] = field(default_factory=list)
    #: Columns forced through masking regardless of inferred role
    force_mask_columns: List[str] = field(default_factory=list)
    #: Deterministic run seed. Same seed => same surrogates.
    seed: str = "aethermask-default-seed"
    enable_statistical_ner: bool = True
    verify_fidelity: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(d: Mapping[str, Any]) -> "TransformConfig":
        base = TransformConfig()
        for k, v in (d or {}).items():
            if hasattr(base, k) and v is not None:
                setattr(base, k, v)
        return base

    def validate(self) -> None:
        if self.numeric_mode not in ("identity", "affine"):
            raise EngineError("numeric_mode must be 'identity' or 'affine'")
        if self.numeric_mode == "affine" and self.affine_scale == 0:
            raise EngineError("affine_scale must be non-zero to remain invertible")


# --------------------------------------------------------------------------- #
#  Bijective map
# --------------------------------------------------------------------------- #
class BijectiveMap:
    """
    A strictly 1↔1 dictionary with an O(1) inverse and collision rejection.

    `put` raises on any attempt to (a) remap an existing key to a new value or
    (b) assign an already-used value to a different key. That makes many-to-one
    collapse structurally impossible rather than merely unlikely.
    """

    __slots__ = ("forward", "inverse")

    def __init__(self, forward: Optional[Mapping[str, str]] = None) -> None:
        self.forward: Dict[str, str] = {}
        self.inverse: Dict[str, str] = {}
        if forward:
            for k, v in forward.items():
                self.put(str(k), str(v))

    def put(self, key: str, value: str) -> str:
        cur = self.forward.get(key)
        if cur is not None:
            if cur != value:
                raise EngineError(
                    f"Bijection violation: key {key!r} already maps to {cur!r}; "
                    f"refusing to remap to {value!r}."
                )
            return cur
        owner = self.inverse.get(value)
        if owner is not None and owner != key:
            raise EngineError(
                f"Bijection violation: value {value!r} is already the image of "
                f"{owner!r}; refusing many-to-one collapse for {key!r}."
            )
        self.forward[key] = value
        self.inverse[value] = key
        return value

    def get(self, key: str) -> Optional[str]:
        return self.forward.get(key)

    def has_value(self, value: str) -> bool:
        return value in self.inverse

    def invert(self, value: str) -> Optional[str]:
        return self.inverse.get(value)

    def __len__(self) -> int:
        return len(self.forward)

    def __contains__(self, key: object) -> bool:
        return key in self.forward

    def as_dict(self) -> Dict[str, str]:
        return dict(self.forward)

    def verify(self) -> None:
        """Assert the 1↔1 invariant holds across the whole map."""
        if len(self.forward) != len(self.inverse):
            raise EngineError(
                f"Bijection broken: {len(self.forward)} keys vs "
                f"{len(self.inverse)} distinct images."
            )
        if len(set(self.forward.values())) != len(self.forward):
            raise EngineError("Bijection broken: duplicate images detected.")


# --------------------------------------------------------------------------- #
#  Fidelity report
# --------------------------------------------------------------------------- #
@dataclass
class FidelityReport:
    passed: bool = True
    checks: List[Dict[str, Any]] = field(default_factory=list)
    failures: List[str] = field(default_factory=list)

    def add(self, name: str, table: str, column: str, ok: bool, detail: str = "") -> None:
        self.checks.append(
            {"check": name, "table": table, "column": column, "ok": bool(ok), "detail": detail}
        )
        if not ok:
            self.passed = False
            loc = f"{table}.{column}" if column else table
            self.failures.append(f"[{name}] {loc}: {detail}")

    def summary(self) -> Dict[str, Any]:
        total = len(self.checks)
        ok = sum(1 for c in self.checks if c["ok"])
        return {
            "passed": self.passed,
            "total_checks": total,
            "passed_checks": ok,
            "failed_checks": total - ok,
            "failures": self.failures[:50],
        }

    def to_dict(self) -> Dict[str, Any]:
        return {**self.summary(), "checks": self.checks}


@dataclass
class MaskResult:
    tables: Dict[str, pl.DataFrame]
    mapping_payload: Dict[str, Any]
    fidelity: FidelityReport
    table_name_map: Dict[str, str]
    column_map: Dict[str, str]
    value_map_size: int
    schema_fingerprint: str


@dataclass
class RestoreResult:
    tables: Dict[str, pl.DataFrame]
    table_name_map: Dict[str, str]
    restored_columns: int
    restored_values: int


# --------------------------------------------------------------------------- #
#  Engine
# --------------------------------------------------------------------------- #
class OfflineIsomorphicEngine:
    """
    Deterministic offline semantic obfuscation / de-obfuscation engine.

        engine = OfflineIsomorphicEngine(TransformConfig(...))
        result = engine.mask({"orbat": df})
        back   = engine.restore(result.tables, result.mapping_payload)
    """

    _ID_ALPHA_UPPER = string.ascii_uppercase
    _ID_ALPHA_LOWER = string.ascii_lowercase
    _ID_DIGITS = string.digits

    def __init__(
        self,
        config: Optional[TransformConfig] = None,
        profiler: Optional[SensitivityProfiler] = None,
        ner: Optional[OfflineNER] = None,
    ) -> None:
        self.config = config or TransformConfig()
        self.config.validate()
        self.profile: DomainProfile = get_profile(self.config.domain_profile)
        self.profiler = profiler or SensitivityProfiler()
        self.ner = ner or OfflineNER(
            enable_statistical=self.config.enable_statistical_ner
        )

        self._seed = self.config.seed.encode("utf-8")
        self.columns = BijectiveMap()
        self.values = BijectiveMap()
        self.table_names = BijectiveMap()
        #: column -> {"a": float, "b": float} for affine numeric projections
        self.transform_params: Dict[str, Dict[str, Any]] = {}
        #: per-column semantic bookkeeping recorded into the vault
        self.column_meta: Dict[str, Dict[str, Any]] = {}
        #: pool cursors, keyed by pool name, for deterministic allocation
        self._pool_usage: Dict[str, Set[str]] = {}

    # ================================================================== #
    #  Deterministic primitives
    # ================================================================== #
    def _digest(self, *parts: str) -> bytes:
        msg = b"\x1f".join(p.encode("utf-8") for p in parts)
        return hmac.new(self._seed, msg, hashlib.sha256).digest()

    def _index(self, size: int, *parts: str, probe: int = 0) -> int:
        """Deterministic index in [0, size) with linear probing for collisions."""
        if size <= 0:
            return 0
        d = self._digest(*parts, f"#probe{probe}")
        return int.from_bytes(d[:8], "big") % size

    # ------------------------------------------------------------------ #
    #  Surrogate allocation from an ontology pool
    # ------------------------------------------------------------------ #
    def _alloc_from_pool(self, pool_name: str, source: str) -> str:
        """
        Deterministically allocate an unused surrogate from a named pool.

        If the pool is exhausted, deterministic numeric suffixes extend it
        indefinitely while preserving injectivity.
        """
        pool = list(self.profile.pool(pool_name))
        used = self._pool_usage.setdefault(pool_name, set())

        n = len(pool)
        for probe in range(max(n * 2, 16)):
            idx = self._index(n, pool_name, source, probe=probe)
            cand = pool[idx]
            if cand not in used and not self.values.has_value(cand):
                used.add(cand)
                return cand

        # Pool saturated: deterministic extension with a stable numeric suffix.
        base_idx = self._index(n, pool_name, source)
        base = pool[base_idx] if n else pool_name
        k = 2
        while True:
            cand = f"{base} {k:03d}"
            if cand not in used and not self.values.has_value(cand):
                used.add(cand)
                return cand
            k += 1

    # ------------------------------------------------------------------ #
    #  Format-preserving identifier surrogate
    # ------------------------------------------------------------------ #
    def _format_preserving_token(self, source: str, salt: str = "") -> str:
        """
        Emit a surrogate with the SAME physical shape as `source`:
        uppercase->uppercase, lowercase->lowercase, digit->digit, and every
        other character (dashes, dots, slashes) copied verbatim.

        Deterministic: the surrogate is a keyed stream over the source token.
        """
        if not source:
            return source
        for probe in range(64):
            stream = self._digest("fpt", salt, source, f"#p{probe}")
            # Extend the stream if the token is longer than 32 bytes.
            while len(stream) < len(source):
                stream += self._digest("fpt-ext", salt, source, str(len(stream)))
            out: List[str] = []
            for i, ch in enumerate(source):
                b = stream[i]
                if ch.isdigit():
                    out.append(self._ID_DIGITS[b % 10])
                elif ch.isupper():
                    out.append(self._ID_ALPHA_UPPER[b % 26])
                elif ch.islower():
                    out.append(self._ID_ALPHA_LOWER[b % 26])
                else:
                    out.append(ch)
            cand = "".join(out)
            if cand != source and not self.values.has_value(cand):
                return cand
        # Extremely improbable; guarantee termination with a suffixed form.
        return f"{source[:2]}{self._digest('fpt-final', source).hex()[:10].upper()}"

    # ================================================================== #
    #  Column header transformation
    # ================================================================== #
    def _shift_identifier(self, name: str) -> str:
        """
        Rewrite a column header through the domain token-shift matrix.

        Strategy (deterministic, longest-match-first):
          1. whole-name match on the normalised identifier
          2. substring rewrite of the normalised identifier by ordered keys
          3. per-token rewrite preserving the original delimiters and casing
        """
        norm = normalise_identifier(name)
        shifts = self.profile.token_shifts

        # 1. exact whole-identifier hit
        if norm in shifts:
            return self._match_case(name, shifts[norm])

        # 2. ordered substring rewriting on the normalised form
        rewritten = norm
        changed = False
        for key in self.profile.ordered_shift_keys():
            if key in rewritten:
                rewritten = rewritten.replace(key, shifts[key])
                changed = True
        if changed:
            return self._match_case(name, rewritten)

        # 3. token-wise rewrite keeping original separators/casing
        tokens, seps = split_identifier(name)
        new_tokens: List[str] = []
        any_tok = False
        for tok in tokens:
            low = tok.lower()
            if low in shifts:
                new_tokens.append(self._match_token_case(tok, shifts[low]))
                any_tok = True
            else:
                new_tokens.append(tok)
        if any_tok:
            return rejoin_identifier(new_tokens, seps)

        return name  # semantically neutral header - left intact

    @staticmethod
    def _match_case(original: str, replacement: str) -> str:
        """Project the replacement into the original header's casing style."""
        if original.isupper():
            return replacement.upper()
        if original.islower():
            return replacement.lower()
        if original and original[0].isupper() and original[1:].islower():
            return replacement.capitalize()
        # camelCase / PascalCase detection
        if re.search(r"[a-z][A-Z]", original):
            parts = replacement.split("_")
            head = parts[0]
            if original[0].isupper():
                head = head.capitalize()
            return head + "".join(p.capitalize() for p in parts[1:])
        return replacement

    @staticmethod
    def _match_token_case(original: str, replacement: str) -> str:
        if original.isupper():
            return replacement.upper()
        if original[:1].isupper():
            return replacement.capitalize()
        return replacement

    def _allocate_column_name(self, name: str, taken: Set[str]) -> str:
        """Shift a header, then deduplicate deterministically within the table."""
        existing = self.columns.get(name)
        if existing is not None and existing not in taken:
            return existing
        if existing is not None:
            return existing

        base = self._shift_identifier(name) if self.config.mask_column_names else name
        cand = base
        n = 2
        while cand in taken or (self.columns.has_value(cand) and self.columns.invert(cand) != name):
            cand = f"{base}_{n}"
            n += 1
        self.columns.put(name, cand)
        return cand

    # ================================================================== #
    #  Value transformation
    # ================================================================== #
    def _map_categorical(self, value: str, pool_name: str) -> str:
        existing = self.values.get(value)
        if existing is not None:
            return existing
        surrogate = self._alloc_from_pool(pool_name, value)
        return self.values.put(value, surrogate)

    def _map_identifier(self, value: str, column: str) -> str:
        existing = self.values.get(value)
        if existing is not None:
            return existing
        if self.config.format_preserving_ids:
            surrogate = self._format_preserving_token(value, salt="id")
        else:
            surrogate = f"ID-{self._digest('seq', column, value).hex()[:12].upper()}"
            probe = 0
            while self.values.has_value(surrogate):
                probe += 1
                surrogate = f"ID-{self._digest('seq', column, value, str(probe)).hex()[:12].upper()}"
        return self.values.put(value, surrogate)

    def _map_free_text(self, text: str) -> str:
        """Rewrite narrative text, bijectively substituting recognised entities."""
        def resolver(ent: Entity) -> str:
            return self._map_categorical(ent.text, ent.pool)

        rewritten, _ = self.ner.rewrite(text, resolver)
        return rewritten

    # ------------------------------------------------------------------ #
    #  Pool selection for a column
    # ------------------------------------------------------------------ #
    @staticmethod
    def _pool_for_column(col_name: str, role: str, findings: Sequence[Mapping[str, Any]]) -> str:
        n = normalise_identifier(col_name)
        cats = {str(f.get("category")) for f in findings}
        if "classification" in cats:
            return "HANDLING_TIER"

        # Ordered most-specific -> least-specific. Domain nouns are tested
        # BEFORE the generic "name" token so that headers such as
        # "operation_name" or "installation_name" resolve on their domain noun
        # rather than on the trailing "_name" suffix.
        rules: Sequence[Tuple[Tuple[str, ...], str]] = (
            (("callsign", "call_sign", "tail_number", "hull_number", "registration"), "ASSET"),
            (("project", "program", "programme", "operation", "mission", "campaign",
              "exercise", "consignment", "task_force"), "PROJECT"),
            (("squadron", "fleet", "battalion", "regiment", "brigade", "org",
              "company", "vendor", "contractor", "agency", "supplier", "carrier",
              "operator_org", "wing"), "ORG"),
            (("installation", "airfield", "airbase", "base", "site", "facility",
              "depot", "port", "station", "terminal", "hub", "warehouse",
              "location", "plant", "substation"), "SITE"),
            (("target", "waypoint", "destination", "designation", "aimpoint",
              "dropoff", "objective"), "SITE"),
            (("route", "corridor", "lane", "track", "path", "leg"), "ROUTE"),
            (("asset", "platform", "aircraft", "airframe", "vehicle", "vessel",
              "ship", "weapon", "system", "equipment", "hauler"), "ASSET"),
            (("person", "operator", "pilot", "officer", "employee", "handler",
              "crew_member", "commander", "manager", "author", "owner",
              "full_name", "first_name", "last_name", "display_name"), "PERSON"),
            (("region", "district", "country", "province", "city", "area",
              "sector", "theater", "theatre", "zone", "territory"), "PLACE"),
            (("status", "phase", "condition", "readiness", "disposition",
              "threat", "risk", "priority", "severity", "grade", "tier",
              "level", "state"), "STATUS"),
            (("name", "label", "title"), "PERSON"),
        )
        for keys, pool in rules:
            if any(k in n for k in keys):
                return pool
        return "GENERIC"

    # ================================================================== #
    #  MASK
    # ================================================================== #
    def mask(
        self,
        tables: Mapping[str, pl.DataFrame],
        profiles: Optional[Mapping[str, TableProfile]] = None,
        source_manifest: Optional[Mapping[str, Any]] = None,
    ) -> MaskResult:
        """Transform every table into its isomorphic, non-classified image."""
        from .security import CipherVault

        if not tables:
            raise EngineError("No tables supplied to mask().")

        profs: Dict[str, TableProfile] = dict(profiles) if profiles else {}
        for tname, df in tables.items():
            if tname not in profs:
                profs[tname] = self.profiler.profile_table(df, tname)

        original_schema = {
            t: [(c.name, c.dtype) for c in profs[t].columns] for t in tables
        }
        schema_fp = CipherVault.multi_table_fingerprint(original_schema)

        masked: Dict[str, pl.DataFrame] = {}
        for tname, df in tables.items():
            masked[tname] = self._mask_table(tname, df, profs[tname])

        # Table names (recorded; applied at serialisation time)
        tmap: Dict[str, str] = {}
        for tname in tables:
            if self.config.mask_table_names:
                shifted = self._shift_identifier(tname)
                cand = shifted
                k = 2
                while self.table_names.has_value(cand) and self.table_names.invert(cand) != tname:
                    cand = f"{shifted}_{k}"
                    k += 1
                tmap[tname] = self.table_names.put(tname, cand)
            else:
                tmap[tname] = tname

        self.columns.verify()
        self.values.verify()

        fidelity = FidelityReport()
        if self.config.verify_fidelity:
            fidelity = self.verify_fidelity(tables, masked, profs)
            if not fidelity.passed:
                raise FidelityError(
                    "Statistical isomorphism verification FAILED:\n  "
                    + "\n  ".join(fidelity.failures[:20])
                )

        payload: Dict[str, Any] = {
            "engine_version": ENGINE_VERSION,
            "domain_profile": self.config.domain_profile,
            "config": self.config.to_dict(),
            "columns": self.columns.as_dict(),
            "values": self.values.as_dict(),
            "table_names": self.table_names.as_dict(),
            "transform_params": self.transform_params,
            "column_meta": self.column_meta,
            "schema": {
                t: [[c.name, c.dtype] for c in profs[t].columns] for t in tables
            },
            "masked_schema": {
                t: [[c, str(masked[t].get_column(c).dtype)] for c in masked[t].columns]
                for t in masked
            },
            "row_counts": {t: tables[t].height for t in tables},
            "source_manifest": dict(source_manifest) if source_manifest else {},
            "schema_fingerprint": schema_fp,
        }

        return MaskResult(
            tables=masked,
            mapping_payload=payload,
            fidelity=fidelity,
            table_name_map=tmap,
            column_map=self.columns.as_dict(),
            value_map_size=len(self.values),
            schema_fingerprint=schema_fp,
        )

    # ------------------------------------------------------------------ #
    def _mask_table(self, tname: str, df: pl.DataFrame, prof: TableProfile) -> pl.DataFrame:
        if df.width == 0:
            return df.clone()

        taken: Set[str] = set()
        new_columns: List[pl.Series] = []

        for col in prof.columns:
            name = col.name
            series = df.get_column(name)
            qualified = f"{tname}.{name}"

            passthrough = name in self.config.passthrough_columns or qualified in self.config.passthrough_columns
            forced = name in self.config.force_mask_columns or qualified in self.config.force_mask_columns

            new_name = self._allocate_column_name(name, taken)
            taken.add(new_name)

            role = col.semantic_role
            pool = self._pool_for_column(name, role, col.findings)

            meta: Dict[str, Any] = {
                "table": tname,
                "original_name": name,
                "masked_name": new_name,
                "dtype": col.dtype,
                "role": role,
                "pool": pool,
                "strategy": "passthrough",
                "null_count": col.null_count,
                "distinct_count": col.distinct_count,
            }

            if passthrough and not forced:
                new_series = series.rename(new_name)
                self.column_meta[qualified] = meta
                new_columns.append(new_series)
                continue

            if series.dtype.is_numeric():
                new_series, strategy = self._mask_numeric(series, name, role, qualified)
            elif series.dtype in (pl.Date, pl.Datetime, pl.Time, pl.Duration, pl.Boolean):
                # Temporal & boolean columns are structurally preserved so that
                # every time-series trendline is bit-identical.
                new_series, strategy = series, "preserved"
            else:
                new_series, strategy = self._mask_stringlike(series, name, role, pool, col, forced)

            meta["strategy"] = strategy
            self.column_meta[qualified] = meta
            new_columns.append(new_series.rename(new_name))

        return pl.DataFrame(new_columns)

    # ------------------------------------------------------------------ #
    def _mask_numeric(
        self, series: pl.Series, name: str, role: str, qualified: str
    ) -> Tuple[pl.Series, str]:
        cfg = self.config

        # Numeric identifiers are relabelled (as text-preserving integers) only
        # when they are genuine keys; measures are never disturbed.
        if role == SemanticRole.IDENTIFIER and cfg.mask_identifiers:
            mapped = self._mask_numeric_identifier(series, name)
            return mapped, "numeric_identifier_bijection"

        if cfg.numeric_mode == "affine":
            is_geo = role == SemanticRole.GEOSPATIAL
            if (cfg.affine_geo_only and is_geo) or (not cfg.affine_geo_only):
                a, b = float(cfg.affine_scale), float(cfg.affine_offset)
                if a == 0:
                    raise EngineError("affine_scale must be non-zero")
                self.transform_params[qualified] = {
                    "kind": "affine", "a": a, "b": b, "dtype": str(series.dtype),
                }
                out = (series.cast(pl.Float64, strict=False) * a + b)
                if series.dtype in (pl.Int8, pl.Int16, pl.Int32, pl.Int64,
                                    pl.UInt8, pl.UInt16, pl.UInt32, pl.UInt64):
                    # Preserve integrality only when the projection is integral.
                    if float(a).is_integer() and float(b).is_integer():
                        out = out.cast(series.dtype, strict=False)
                        self.transform_params[qualified]["integral"] = True
                return out.rename(series.name), "affine"

        return series, "identity"

    def _mask_numeric_identifier(self, series: pl.Series, name: str) -> pl.Series:
        """
        Bijectively relabel a numeric key while keeping the numeric dtype and
        the digit-width, so joins and any downstream integer arithmetic on the
        key space continue to behave identically.
        """
        out: List[Optional[int]] = []
        for v in series.to_list():
            if v is None:
                out.append(None)
                continue
            src = str(v)
            existing = self.values.get(src)
            if existing is None:
                token = self._format_preserving_token(src, salt="numid")
                # Guarantee it parses as an integer of identical width.
                digits = "".join(ch for ch in token if ch.isdigit())
                if not digits:
                    digits = self._digest("numid-fb", src).hex()
                    digits = "".join(c for c in digits if c.isdigit()) or "1"
                digits = digits[: max(1, len(src.lstrip("-")))].rjust(
                    max(1, len(src.lstrip("-"))), "0"
                )
                cand = ("-" if src.startswith("-") else "") + digits
                probe = 0
                while self.values.has_value(cand):
                    probe += 1
                    d2 = self._digest("numid", src, str(probe)).hex()
                    d2 = "".join(c for c in d2 if c.isdigit()) or "1"
                    d2 = d2[: max(1, len(src.lstrip("-")))].rjust(
                        max(1, len(src.lstrip("-"))), "0"
                    )
                    cand = ("-" if src.startswith("-") else "") + d2
                existing = self.values.put(src, cand)
            try:
                out.append(int(existing))
            except ValueError:
                out.append(None)
        dtype = series.dtype if series.dtype in (
            pl.Int8, pl.Int16, pl.Int32, pl.Int64,
            pl.UInt8, pl.UInt16, pl.UInt32, pl.UInt64,
        ) else pl.Int64
        return pl.Series(series.name, out, dtype=dtype, strict=False)

    # ------------------------------------------------------------------ #
    def _mask_stringlike(
        self, series: pl.Series, name: str, role: str, pool: str,
        col_profile, forced: bool,
    ) -> Tuple[pl.Series, str]:
        cfg = self.config
        s = series.cast(pl.Utf8, strict=False)

        if role == SemanticRole.EMPTY:
            return s.rename(series.name), "empty"

        if role == SemanticRole.FREE_TEXT:
            if not cfg.mask_free_text and not forced:
                return s.rename(series.name), "passthrough"
            vals = [None if v is None else self._map_free_text(v) for v in s.to_list()]
            return pl.Series(series.name, vals, dtype=pl.Utf8), "free_text_ner"

        if role == SemanticRole.IDENTIFIER:
            if not cfg.mask_identifiers and not forced:
                return s.rename(series.name), "passthrough"
            vals = [
                None if v is None else self._map_identifier(v, name) for v in s.to_list()
            ]
            return pl.Series(series.name, vals, dtype=pl.Utf8), "identifier_bijection"

        # CATEGORICAL / CONSTANT / GEOSPATIAL-as-text / anything else textual
        if not cfg.mask_categoricals and not forced:
            return s.rename(series.name), "passthrough"

        # Build the bijection over the DISTINCT domain only, then vectorise the
        # substitution. Frequencies are therefore preserved exactly.
        distinct = [v for v in s.unique(maintain_order=True).to_list() if v is not None]
        local_map: Dict[str, str] = {}
        for v in sorted(distinct):  # sorted => allocation order is deterministic
            local_map[v] = self._map_categorical(v, pool)

        mapped = s.replace_strict(
            old=list(local_map.keys()), new=list(local_map.values()),
            default=None, return_dtype=pl.Utf8,
        )
        return mapped.rename(series.name), "categorical_bijection"

    # ================================================================== #
    #  FIDELITY VERIFICATION
    # ================================================================== #
    def verify_fidelity(
        self,
        original: Mapping[str, pl.DataFrame],
        masked: Mapping[str, pl.DataFrame],
        profiles: Mapping[str, TableProfile],
    ) -> FidelityReport:
        """
        Assert the statistical isomorphism guarantees, table by table.

        Checks performed
        ----------------
          * table set equality and row counts
          * column count and one-to-one header correspondence
          * per-column null count equality
          * per-column distinct cardinality equality
          * categorical frequency-distribution equality (sorted count multiset)
          * numeric aggregate equality (identity mode) or exact affine recovery
          * bijection integrity (no many-to-one collapse)
        """
        rep = FidelityReport()

        rep.add(
            "table_set", "*", "",
            set(original.keys()) == set(masked.keys()),
            f"original={sorted(original)} masked={sorted(masked)}",
        )

        for tname, odf in original.items():
            mdf = masked.get(tname)
            if mdf is None:
                rep.add("table_present", tname, "", False, "masked table missing")
                continue

            rep.add(
                "row_count", tname, "", odf.height == mdf.height,
                f"{odf.height} vs {mdf.height}",
            )
            rep.add(
                "column_count", tname, "", odf.width == mdf.width,
                f"{odf.width} vs {mdf.width}",
            )
            if odf.width != mdf.width:
                continue

            prof = profiles[tname]
            for i, ocol in enumerate(odf.columns):
                mcol = mdf.columns[i]
                os_ = odf.get_column(ocol)
                ms_ = mdf.get_column(mcol)
                cprof = prof.column(ocol)
                role = cprof.semantic_role if cprof else SemanticRole.CATEGORICAL

                rep.add(
                    "null_count", tname, ocol,
                    int(os_.null_count()) == int(ms_.null_count()),
                    f"{os_.null_count()} vs {ms_.null_count()}",
                )

                try:
                    o_card = int(os_.cast(pl.Utf8, strict=False).n_unique())
                    m_card = int(ms_.cast(pl.Utf8, strict=False).n_unique())
                except Exception:
                    o_card = m_card = -1
                rep.add(
                    "cardinality", tname, ocol, o_card == m_card,
                    f"{o_card} vs {m_card}",
                )

                # Frequency-distribution equality (the core isomorphism claim).
                if role in (
                    SemanticRole.CATEGORICAL, SemanticRole.BOOLEAN,
                    SemanticRole.CONSTANT, SemanticRole.IDENTIFIER,
                    SemanticRole.FREE_TEXT,
                ):
                    try:
                        o_counts = sorted(
                            odf.select(pl.col(ocol).cast(pl.Utf8, strict=False))
                            .to_series().value_counts()[:, -1].to_list()
                        )
                        m_counts = sorted(
                            mdf.select(pl.col(mcol).cast(pl.Utf8, strict=False))
                            .to_series().value_counts()[:, -1].to_list()
                        )
                        rep.add(
                            "frequency_distribution", tname, ocol,
                            o_counts == m_counts,
                            f"histograms differ ({len(o_counts)} vs {len(m_counts)} buckets)"
                            if o_counts != m_counts else "identical",
                        )
                    except Exception as exc:
                        rep.add("frequency_distribution", tname, ocol, False, str(exc))

                # Numeric fidelity
                if os_.dtype.is_numeric() and ms_.dtype.is_numeric():
                    qualified = f"{tname}.{ocol}"
                    params = self.transform_params.get(qualified)
                    if params is None and role != SemanticRole.IDENTIFIER:
                        for stat in ("sum", "mean", "min", "max"):
                            ov = getattr(os_, stat)()
                            mv = getattr(ms_, stat)()
                            ok = self._num_eq(ov, mv)
                            rep.add(
                                f"numeric_{stat}", tname, ocol, ok, f"{ov} vs {mv}"
                            )
                    elif params is not None and params.get("kind") == "affine":
                        a, b = float(params["a"]), float(params["b"])
                        recovered = (ms_.cast(pl.Float64, strict=False) - b) / a
                        ok = self._series_close(os_.cast(pl.Float64, strict=False), recovered)
                        rep.add(
                            "affine_invertibility", tname, ocol, ok,
                            "inverse projection did not recover the source values",
                        )

        try:
            self.columns.verify()
            rep.add("bijection_columns", "*", "", True, f"{len(self.columns)} headers")
        except EngineError as exc:
            rep.add("bijection_columns", "*", "", False, str(exc))
        try:
            self.values.verify()
            rep.add("bijection_values", "*", "", True, f"{len(self.values)} tokens")
        except EngineError as exc:
            rep.add("bijection_values", "*", "", False, str(exc))

        return rep

    @staticmethod
    def _num_eq(a: Any, b: Any, tol: float = 1e-9) -> bool:
        if a is None and b is None:
            return True
        if a is None or b is None:
            return False
        try:
            fa, fb = float(a), float(b)
        except (TypeError, ValueError):
            return a == b
        if fa == fb:
            return True
        scale = max(abs(fa), abs(fb), 1.0)
        return abs(fa - fb) <= tol * scale

    @classmethod
    def _series_close(cls, a: pl.Series, b: pl.Series, tol: float = 1e-6) -> bool:
        if a.len() != b.len():
            return False
        for x, y in zip(a.to_list(), b.to_list()):
            if x is None and y is None:
                continue
            if x is None or y is None:
                return False
            if abs(float(x) - float(y)) > tol * max(1.0, abs(float(x))):
                return False
        return True

    # ================================================================== #
    #  RESTORE
    # ================================================================== #
    @classmethod
    def restore(
        cls,
        masked_tables: Mapping[str, pl.DataFrame],
        mapping_payload: Mapping[str, Any],
        strict: bool = False,
    ) -> RestoreResult:
        """
        Invert the bijection and rebuild the confidential dataset.

        Works on the masked dataset itself AND on any downstream analytical
        output (aggregates, pivot tables, model scorecards) that carries masked
        headers or masked category labels - because inversion is performed on
        the token lattice, not on row identity.

        `strict=True` raises when a masked token is absent from the vault;
        the default leaves unknown tokens untouched so that derived artifacts
        containing new computed columns still restore cleanly.
        """
        col_fwd: Dict[str, str] = dict(mapping_payload.get("columns", {}))
        val_fwd: Dict[str, str] = dict(mapping_payload.get("values", {}))
        tbl_fwd: Dict[str, str] = dict(mapping_payload.get("table_names", {}))
        params: Dict[str, Any] = dict(mapping_payload.get("transform_params", {}))
        schema: Dict[str, Any] = dict(mapping_payload.get("schema", {}))
        column_meta: Dict[str, Any] = dict(mapping_payload.get("column_meta", {}))

        col_inv = {v: k for k, v in col_fwd.items()}
        val_inv = {v: k for k, v in val_fwd.items()}
        tbl_inv = {v: k for k, v in tbl_fwd.items()}

        # Index the per-column metadata by MASKED column name as well as by the
        # table-qualified key. A sanitized artifact is frequently re-ingested
        # under a different table/sheet/file stem than the one it was masked
        # under (e.g. "missions" -> "missions_sanitized"), which would make a
        # strictly table-qualified lookup miss and silently skip the correct
        # inversion strategy. Keying on the masked column name makes restoration
        # independent of how the artifact was named or re-ingested.
        meta_by_masked: Dict[str, Dict[str, Any]] = {}
        for _qkey, _meta in column_meta.items():
            if isinstance(_meta, dict):
                mk = str(_meta.get("masked_name", ""))
                if mk and mk not in meta_by_masked:
                    meta_by_masked[mk] = _meta

        if len(col_inv) != len(col_fwd) or len(val_inv) != len(val_fwd):
            raise EngineError(
                "Vault integrity failure: the stored mapping is not bijective, "
                "so lossless inversion is impossible."
            )

        # masked table name -> original
        restored: Dict[str, pl.DataFrame] = {}
        name_map: Dict[str, str] = {}
        n_cols = 0
        n_vals = 0

        for mname, mdf in masked_tables.items():
            oname = tbl_inv.get(mname, mname)
            name_map[mname] = oname

            # dtype targets from the original schema, indexed by original name
            target_types: Dict[str, str] = {}
            for entry in schema.get(oname, []):
                if isinstance(entry, (list, tuple)) and len(entry) == 2:
                    target_types[str(entry[0])] = str(entry[1])

            out_series: List[pl.Series] = []
            for mcol in mdf.columns:
                ocol = col_inv.get(mcol, mcol)
                if ocol != mcol:
                    n_cols += 1
                elif strict and mcol not in col_inv and mcol not in col_fwd:
                    raise EngineError(f"Unknown masked column '{mcol}' in vault.")

                s = mdf.get_column(mcol)
                qualified = f"{oname}.{ocol}"
                meta = column_meta.get(qualified) or meta_by_masked.get(mcol) or {}
                strategy = str(meta.get("strategy", ""))
                target = target_types.get(ocol) or (
                    str(meta.get("dtype")) if meta.get("dtype") else None
                )

                aff = params.get(qualified)
                if aff is None and meta.get("original_name"):
                    aff = params.get(f"{oname}.{meta['original_name']}")
                if aff is None:
                    aff = next(
                        (v for k, v in params.items()
                         if k.rsplit(".", 1)[-1] == ocol), None
                    )
                if aff is not None and aff.get("kind") == "affine":
                    a = float(aff["a"])
                    b = float(aff["b"])
                    inv = (s.cast(pl.Float64, strict=False) - b) / a
                    out_series.append(
                        cls._cast_to(inv.rename(ocol), target, integral=True)
                    )
                    continue

                if strategy in ("identity", "preserved", "empty", "passthrough", "affine"):
                    out_series.append(cls._cast_to(s.rename(ocol), target))
                    continue

                # Non-textual columns can never carry surrogate tokens, so they
                # are passed through untouched. This is what allows a DOWNSTREAM
                # ANALYTICAL OUTPUT (a group-by with computed measures such as
                # "total_sorties" that never existed in the source schema) to be
                # re-identified without its numeric results being stringified.
                if not (s.dtype == pl.Utf8 or s.dtype == pl.Categorical):
                    if strategy != "numeric_identifier_bijection":
                        out_series.append(cls._cast_to(s.rename(ocol), target))
                        continue

                # Unknown/derived textual column with no vault provenance:
                # invert only tokens the vault actually knows, never coerce.
                # Token inversion path
                txt = s.cast(pl.Utf8, strict=False)
                distinct = [v for v in txt.unique(maintain_order=True).to_list() if v is not None]
                local: Dict[str, str] = {}
                for v in distinct:
                    orig = val_inv.get(v)
                    if orig is None:
                        if strict:
                            raise EngineError(
                                f"Token {v!r} in column '{mcol}' is absent from the vault."
                            )
                        local[v] = v
                    else:
                        local[v] = orig
                        n_vals += 1

                if strategy == "free_text_ner":
                    rebuilt = [
                        None if v is None else cls._invert_text(v, val_inv)
                        for v in txt.to_list()
                    ]
                    inv_s = pl.Series(ocol, rebuilt, dtype=pl.Utf8)
                else:
                    inv_s = txt.replace_strict(
                        old=list(local.keys()), new=list(local.values()),
                        default=None, return_dtype=pl.Utf8,
                    ).rename(ocol)

                out_series.append(cls._cast_to(inv_s, target))

            restored[oname] = pl.DataFrame(out_series)

        return RestoreResult(
            tables=restored,
            table_name_map=name_map,
            restored_columns=n_cols,
            restored_values=n_vals,
        )

    # ------------------------------------------------------------------ #
    @staticmethod
    def _invert_text(text: str, val_inv: Mapping[str, str]) -> str:
        """
        Restore narrative text by substituting every known surrogate back.

        Longest surrogates are replaced first so that a short surrogate can
        never corrupt a longer one that contains it.
        """
        out = text
        # Only consider surrogates actually present - keeps this near-linear.
        present = [s for s in val_inv if s and s in out]
        for surrogate in sorted(present, key=len, reverse=True):
            out = out.replace(surrogate, val_inv[surrogate])
        return out

    @staticmethod
    def _cast_to(s: pl.Series, dtype_str: Optional[str], integral: bool = False) -> pl.Series:
        """Best-effort restoration of the original physical dtype."""
        if not dtype_str:
            return s
        name = s.name
        try:
            d = dtype_str.strip()
            mapping = {
                "Int8": pl.Int8, "Int16": pl.Int16, "Int32": pl.Int32, "Int64": pl.Int64,
                "UInt8": pl.UInt8, "UInt16": pl.UInt16, "UInt32": pl.UInt32, "UInt64": pl.UInt64,
                "Float32": pl.Float32, "Float64": pl.Float64,
                "Boolean": pl.Boolean, "String": pl.Utf8, "Utf8": pl.Utf8,
                "Date": pl.Date, "Time": pl.Time,
            }
            if d.startswith("Datetime"):
                return s.cast(pl.Datetime, strict=False).rename(name)
            if d.startswith("Duration"):
                return s.cast(pl.Duration, strict=False).rename(name)
            target = mapping.get(d)
            if target is None:
                return s
            if integral and target in (
                pl.Int8, pl.Int16, pl.Int32, pl.Int64,
                pl.UInt8, pl.UInt16, pl.UInt32, pl.UInt64,
            ):
                return s.round(0).cast(target, strict=False).rename(name)
            return s.cast(target, strict=False).rename(name)
        except Exception:
            return s

    # ================================================================== #
    #  Diagnostics
    # ================================================================== #
    def describe(self) -> Dict[str, Any]:
        return {
            "engine_version": ENGINE_VERSION,
            "domain_profile": self.profile.key,
            "profile_title": self.profile.title,
            "token_rules": len(self.profile.token_shifts),
            "columns_mapped": len(self.columns),
            "values_mapped": len(self.values),
            "tables_mapped": len(self.table_names),
            "affine_columns": len(self.transform_params),
            "ner_backend": self.ner.backend,
            "network_access": "none",
        }
