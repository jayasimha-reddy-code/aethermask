"""
AetherMask :: API integration suite
===================================
Exercises every endpoint through the real ASGI stack, including a full
profile -> obfuscate -> restore round-trip proving byte-level restoration
of the confidential CSV.
"""
from __future__ import annotations

import base64
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Keep Argon2 cheap for CI; production defaults stay 256 MiB / t=4.
os.environ.setdefault("AETHERMASK_ARGON2_MEMORY_KIB", "32768")
os.environ.setdefault("AETHERMASK_ARGON2_TIME", "2")
os.environ.setdefault("AETHERMASK_ARGON2_PARALLELISM", "1")

import polars as pl
from fastapi.testclient import TestClient

from api.server import app

SAMPLES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "samples")
PASSED, FAILED = [], []


def check(name, cond, detail=""):
    if cond:
        PASSED.append(name)
        print(f"  \033[92mPASS\033[0m  {name}")
    else:
        FAILED.append(f"{name}: {detail}")
        print(f"  \033[91mFAIL\033[0m  {name}  {detail}")
        assert cond, f"API check failed: {name} {detail}"


def section(t):
    print(f"\n\033[1m{t}\033[0m")
    print("-" * 74)


def main() -> int:
    client = TestClient(app)
    csv_path = os.path.join(SAMPLES, "classified_missions.csv")
    with open(csv_path, "rb") as fh:
        csv_bytes = fh.read()
    PW = "Air-Gapped-Vault-2026!"

    section("HEALTH / PROFILES / ATTESTATION")
    r = client.get("/api/v1/health")
    check("GET /health 200", r.status_code == 200, r.text[:120])
    check("health reports airgapped", r.json().get("airgapped") is True)

    r = client.get("/api/v1/profiles")
    _pj = r.json()
    _pkeys = {p["key"] for p in _pj.get("profiles", [])}
    # The catalogue grows as cover domains are added; assert the contract
    # (count matches payload, all v1.0 domains still present, new lexicon
    # domains registered) rather than a brittle hard-coded total.
    check(
        "GET /profiles count matches payload",
        _pj.get("count") == len(_pj.get("profiles", [])) and _pj.get("count") >= 8,
        r.text[:160],
    )
    check(
        "GET /profiles retains all v1.0 domains",
        {
            "defense_to_logistics",
            "aerospace_to_civil_aviation",
            "cyberwar_to_smartgrid",
            "nuclear_to_civil_energy",
            "naval_to_commercial_shipping",
            "generic_pii_redaction",
        }.issubset(_pkeys),
        sorted(_pkeys),
    )
    check(
        "GET /profiles exposes expanded lexicon domains",
        {"biodefence_to_agriculture", "finint_to_retail_analytics"}.issubset(_pkeys),
        sorted(_pkeys),
    )
    check(
        "GET /profiles entries are fully described",
        all(
            all(p.get(f) for f in ("key", "title", "source_domain",
                                   "cover_domain", "description", "token_rules"))
            for p in _pj.get("profiles", [])
        ),
        r.text[:160],
    )

    r = client.get("/api/v1/attestation")
    a = r.json()
    check("attestation: no external APIs", a["airgap"]["external_apis"] == "none")
    check("attestation: AES-256-GCM reported",
          "AES-256-GCM" in a["cryptography"]["aead"])
    check("attestation: Argon2id backend active",
          "argon2" in a["cryptography"]["argon2_backend"])
    check("CSP header is self-only",
          "default-src 'self'" in r.headers.get("content-security-policy", ""))

    section("POST /api/v1/profile")
    r = client.post(
        "/api/v1/profile",
        files={"file": ("classified_missions.csv", csv_bytes, "text/csv")},
    )
    check("profile 200", r.status_code == 200, r.text[:200])
    p = r.json()
    check("risk grade computed", p["risk_grade"] in ("LOW", "MODERATE", "HIGH", "CRITICAL"),
          p.get("risk_grade"))
    check("recommends defense_to_logistics",
          p["recommended_profile"] == "defense_to_logistics", p.get("recommended_profile"))
    check("schema introspected (17 cols)",
          len(p["tables"][0]["columns"]) == 17, str(len(p["tables"][0]["columns"])))
    check("primary key detected",
          "mission_id" in p["tables"][0]["primary_key_candidates"],
          str(p["tables"][0]["primary_key_candidates"]))
    blob = json.dumps(p)
    check("profile response does not leak raw classified values",
          "Target BASTION" not in blob and "12th Strike Squadron" not in blob)
    check("sensitivity findings present",
          any(c["findings"] for c in p["tables"][0]["columns"]))

    section("POST /api/v1/preview")
    r = client.post(
        "/api/v1/preview",
        files={"file": ("classified_missions.csv", csv_bytes, "text/csv")},
        data={"domain_profile": "defense_to_logistics", "seed": "prev"},
    )
    check("preview 200", r.status_code == 200, r.text[:200])
    pv = r.json()
    check("preview has split-screen frames",
          "original" in pv and "sanitized" in pv)
    check("preview chart series are equal-valued",
          [x["value"] for x in pv["chart"]["original_series"]]
          == [x["value"] for x in pv["chart"]["sanitized_series"]],
          "series differ")
    check("preview column map shifts headers",
          pv["column_map"].get("strike_squadron") == "logistics_fleet",
          str(pv["column_map"].get("strike_squadron")))
    check("preview fidelity passed", pv["fidelity"]["passed"])

    section("POST /api/v1/obfuscate")
    r = client.post(
        "/api/v1/obfuscate",
        files={"file": ("classified_missions.csv", csv_bytes, "text/csv")},
        data={
            "passphrase": PW,
            "domain_profile": "defense_to_logistics",
            "seed": "api-test-seed",
        },
    )
    check("obfuscate 200", r.status_code == 200, r.text[:300])
    ob = r.json()
    check("fidelity verification passed", ob["fidelity"]["passed"],
          str(ob["fidelity"].get("failures"))[:200])
    check("artifact returned", ob["artifact"]["size_bytes"] > 1000)
    cm = ob["ciphermap"]["manifest"]
    check("ciphermap suite correct", cm["cipher_suite"] == "AES-256-GCM-Argon2id")
    check("ciphermap has schema fingerprint", len(cm["schema_fingerprint"]) == 64)

    masked_csv = base64.b64decode(ob["artifact"]["base64"])
    txt = masked_csv.decode()
    leaks = [s for s in ("strike_squadron", "warhead", "TOP SECRET",
                         "Target BASTION", "12th Strike Squadron", "defnet.mil")
             if s in txt]
    check("sanitized artifact contains no classified tokens", not leaks, str(leaks))
    check("sanitized artifact uses civil cover terms",
          "logistics_fleet" in txt and "waypoint_lat" in txt)

    vault_blob = json.dumps(cm)
    check("vault leaks no plaintext mapping",
          "strike_squadron" not in vault_blob and "BASTION" not in vault_blob)

    section("POST /api/v1/restore  (lossless round-trip)")
    r = client.post(
        "/api/v1/restore",
        files={
            "file": ("sanitized.csv", masked_csv, "text/csv"),
            "ciphermap": ("m.ciphermap", json.dumps(cm).encode(), "application/json"),
        },
        data={"passphrase": PW, "verify_artifact_digest": "true"},
    )
    check("restore 200", r.status_code == 200, r.text[:300])
    rs = r.json()
    restored = base64.b64decode(rs["artifact"]["base64"])

    orig_df = pl.read_csv(io.BytesIO(csv_bytes), try_parse_dates=True)
    rest_df = pl.read_csv(io.BytesIO(restored), try_parse_dates=True)
    check("restored column names identical",
          list(orig_df.columns) == list(rest_df.columns),
          str(list(rest_df.columns)[:5]))
    check("restored row count identical", orig_df.height == rest_df.height)
    same = orig_df.equals(rest_df)
    if not same:
        diff = [c for c in orig_df.columns
                if not orig_df.get_column(c).equals(rest_df.get_column(c))]
        check("restored data EXACTLY equals original", False, f"differing: {diff}")
    else:
        check("restored data EXACTLY equals original", True)

    section("SECURITY NEGATIVE PATHS")
    r = client.post(
        "/api/v1/restore",
        files={
            "file": ("sanitized.csv", masked_csv, "text/csv"),
            "ciphermap": ("m.ciphermap", json.dumps(cm).encode(), "application/json"),
        },
        data={"passphrase": "TotallyWrongPassphrase!"},
    )
    check("wrong passphrase -> 401", r.status_code == 401, str(r.status_code))

    tampered = dict(cm)
    tampered["dataset_name"] = "not_the_original"
    r = client.post(
        "/api/v1/restore",
        files={
            "file": ("sanitized.csv", masked_csv, "text/csv"),
            "ciphermap": ("m.ciphermap", json.dumps(tampered).encode(), "application/json"),
        },
        data={"passphrase": PW},
    )
    check("tampered vault header -> 401/422", r.status_code in (401, 422), str(r.status_code))

    r = client.post(
        "/api/v1/restore",
        files={
            "file": ("wrong.csv", csv_bytes, "text/csv"),
            "ciphermap": ("m.ciphermap", json.dumps(cm).encode(), "application/json"),
        },
        data={"passphrase": PW, "verify_artifact_digest": "true"},
    )
    check("wrong artifact + digest check -> 409", r.status_code == 409, str(r.status_code))

    r = client.post(
        "/api/v1/obfuscate",
        files={"file": ("x.exe", b"MZ\x00binary", "application/octet-stream")},
        data={"passphrase": PW},
    )
    check("unsupported file type -> 415", r.status_code == 415, str(r.status_code))

    r = client.post(
        "/api/v1/obfuscate",
        files={"file": ("classified_missions.csv", csv_bytes, "text/csv")},
        data={"passphrase": "short", "domain_profile": "defense_to_logistics"},
    )
    check("weak passphrase rejected", r.status_code in (400, 422), str(r.status_code))

    r = client.post(
        "/api/v1/obfuscate",
        files={"file": ("classified_missions.csv", csv_bytes, "text/csv")},
        data={"passphrase": PW, "domain_profile": "no_such_profile"},
    )
    check("unknown domain profile -> 400", r.status_code == 400, str(r.status_code))

    section("POST /api/v1/verify")
    r = client.post(
        "/api/v1/verify",
        files={
            "original": ("o.csv", csv_bytes, "text/csv"),
            "sanitized": ("s.csv", masked_csv, "text/csv"),
            "ciphermap": ("m.ciphermap", json.dumps(cm).encode(), "application/json"),
        },
        data={"passphrase": PW},
    )
    check("verify 200", r.status_code == 200, r.text[:200])
    v = r.json()
    check("independent isomorphism audit passed", v["passed"],
          str([c for c in v["checks"] if not c["ok"]])[:200])

    section("MULTI-FORMAT ENDPOINT COVERAGE")
    for fname, mime in (
        ("classified_workbook.xlsx",
         "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        ("classified_missions.parquet", "application/vnd.apache.parquet"),
        ("classified_dump.sql", "application/sql"),
    ):
        with open(os.path.join(SAMPLES, fname), "rb") as fh:
            b = fh.read()
        r = client.post(
            "/api/v1/obfuscate",
            files={"file": (fname, b, mime)},
            data={"passphrase": PW, "domain_profile": "defense_to_logistics",
                  "seed": "fmt"},
        )
        ok = r.status_code == 200 and r.json()["fidelity"]["passed"]
        check(f"obfuscate {fname}", ok,
              r.text[:200] if r.status_code != 200 else "")
        if ok:
            j = r.json()
            art = base64.b64decode(j["artifact"]["base64"])
            r2 = client.post(
                "/api/v1/restore",
                files={
                    "file": (j["artifact"]["filename"], art, mime),
                    "ciphermap": ("m.ciphermap",
                                  json.dumps(j["ciphermap"]["manifest"]).encode(),
                                  "application/json"),
                },
                data={"passphrase": PW},
            )
            check(f"restore {fname}", r2.status_code == 200, r2.text[:200])

    total = len(PASSED) + len(FAILED)
    print("\n" + "=" * 74)
    if FAILED:
        print(f"\033[91m  {len(PASSED)}/{total} PASSED - {len(FAILED)} FAILURE(S)\033[0m")
        for f in FAILED:
            print(f"    - {f}")
        print("=" * 74)
        return 1
    print(f"\033[92m  ALL {total} API CHECKS PASSED\033[0m")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


def test_api_suite() -> None:
    """Pytest entry point for API integration checks."""
    rc = main()
    assert rc == 0, f"API suite failed with {len(FAILED)} failures: {FAILED}"
