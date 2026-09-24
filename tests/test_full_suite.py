"""
AetherMask (CipherShift) :: full verification suite
===================================================
Proves the five mandatory guarantees end-to-end:

  G1  Air-gap                 - no socket may be opened during masking/restore
  G2  Statistical isomorphism - aggregates, histograms, joins, nullability
  G3  Deterministic bijectivity - 1<->1, no collisions, reproducible
  G4  Cryptographic vault     - AES-256-GCM/Argon2id, tamper-evident
  G5  Lossless round-trip     - original == restore(mask(original))

Run:  python3 tests/test_full_suite.py
"""
from __future__ import annotations

import io
import os
import socket
import sys
import traceback
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import polars as pl

from core.engine import (
    BijectiveMap, EngineError, OfflineIsomorphicEngine, TransformConfig,
)
from core.ingest import DataIngestor
from core.profiler import SensitivityProfiler
from core.security import (
    CipherVault, InvalidPassphrase, KDF_FAST, SchemaMismatch, TamperedVault,
)
from core.serialize import ArtifactWriter

SAMPLES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "samples")

_PASSED: List[str] = []
_FAILED: List[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        _PASSED.append(name)
        print(f"  \033[92mPASS\033[0m  {name}")
    else:
        _FAILED.append(f"{name}: {detail}")
        print(f"  \033[91mFAIL\033[0m  {name}  {detail}")


def section(title: str) -> None:
    print(f"\n\033[1m{title}\033[0m")
    print("-" * 74)


# --------------------------------------------------------------------------- #
#  G1 - Air-gap enforcement
# --------------------------------------------------------------------------- #
class _NetworkBlocked(Exception):
    pass


class _SocketGuard:
    """Context manager that makes ANY outbound socket creation raise."""

    def __enter__(self):
        self._orig_socket = socket.socket
        self._orig_create = socket.create_connection
        self._orig_getaddr = socket.getaddrinfo

        def blocked(*a, **k):
            raise _NetworkBlocked("Air-gap violation: socket creation attempted")

        socket.socket = blocked            # type: ignore[assignment]
        socket.create_connection = blocked  # type: ignore[assignment]
        socket.getaddrinfo = blocked        # type: ignore[assignment]
        return self

    def __exit__(self, *exc):
        socket.socket = self._orig_socket            # type: ignore[assignment]
        socket.create_connection = self._orig_create  # type: ignore[assignment]
        socket.getaddrinfo = self._orig_getaddr       # type: ignore[assignment]
        return False


def test_airgap(missions: pl.DataFrame) -> None:
    section("G1  AIR-GAP ENFORCEMENT  (all sockets blocked during full pipeline)")
    try:
        with _SocketGuard():
            eng = OfflineIsomorphicEngine(TransformConfig(seed="airgap-test"))
            res = eng.mask({"missions": missions})
            vault = CipherVault(KDF_FAST)
            man = vault.seal(res.mapping_payload, "AirGapTest-2026!",
                             res.schema_fingerprint, "missions")
            payload = vault.unseal(man, "AirGapTest-2026!")
            back = OfflineIsomorphicEngine.restore(res.tables, payload)
            ok = back.tables["missions"].height == missions.height
        check("full mask->seal->unseal->restore with sockets disabled", ok)
    except _NetworkBlocked as exc:
        check("full pipeline performs zero network I/O", False, str(exc))
    except Exception as exc:
        check("full pipeline runs offline", False, f"{type(exc).__name__}: {exc}")

    # The Postgres DSN guard must reject a public host.
    ing = DataIngestor()
    try:
        ing._assert_local_dsn("postgresql://u:p@example.com:5432/db")
        check("public PostgreSQL DSN is rejected by air-gap policy", False, "not rejected")
    except Exception:
        check("public PostgreSQL DSN is rejected by air-gap policy", True)
    try:
        ing._assert_local_dsn("postgresql://u:p@localhost:5432/db")
        check("loopback PostgreSQL DSN is permitted", True)
    except Exception as exc:
        check("loopback PostgreSQL DSN is permitted", False, str(exc))


# --------------------------------------------------------------------------- #
#  G2 - Statistical isomorphism
# --------------------------------------------------------------------------- #
def test_isomorphism(missions: pl.DataFrame) -> None:
    section("G2  STATISTICAL & MATHEMATICAL ISOMORPHISM")
    eng = OfflineIsomorphicEngine(TransformConfig(seed="iso-test"))
    res = eng.mask({"missions": missions})
    m = res.tables["missions"]
    cmap = res.column_map

    check("engine self-verification passed", res.fidelity.passed,
          "; ".join(res.fidelity.failures[:3]))
    check("row count preserved", missions.height == m.height,
          f"{missions.height} vs {m.height}")
    check("column count preserved", missions.width == m.width)

    # --- numeric aggregates must be bit-identical (identity mode) ----------
    for col in ("warhead_yield_kg", "sorties_flown", "kill_probability",
                "fuel_burn_kg", "target_latitude"):
        mc = cmap.get(col, col)
        o, n = missions.get_column(col), m.get_column(mc)
        same = (
            o.sum() == n.sum() and o.min() == n.min()
            and o.max() == n.max() and o.mean() == n.mean()
        )
        check(f"numeric identity: {col} -> {mc}", same,
              f"sum {o.sum()} vs {n.sum()}")

    # --- categorical frequency distribution --------------------------------
    for col in ("strike_squadron", "threat_level", "classification", "callsign"):
        mc = cmap.get(col, col)
        o = sorted(missions.get_column(col).value_counts()[:, -1].to_list())
        n = sorted(m.get_column(mc).value_counts()[:, -1].to_list())
        check(f"P(X=x) preserved: {col} -> {mc}", o == n, f"{o[:5]} vs {n[:5]}")

    # --- group-by aggregate equivalence (the BI dashboard claim) -----------
    o_agg = (
        missions.group_by("threat_level")
        .agg(pl.col("sorties_flown").sum().alias("s"), pl.len().alias("n"))
        .sort("s", "n")
    )
    m_agg = (
        m.group_by(cmap.get("threat_level", "threat_level"))
        .agg(pl.col(cmap.get("sorties_flown", "sorties_flown")).sum().alias("s"),
             pl.len().alias("n"))
        .sort("s", "n")
    )
    check("GROUP BY aggregate vectors identical",
          o_agg.select("s", "n").to_dicts() == m_agg.select("s", "n").to_dicts(),
          f"{o_agg.select('s','n').to_dicts()} vs {m_agg.select('s','n').to_dicts()}")

    # --- time-series trendline (Recharts equivalence) ----------------------
    o_ts = (
        missions.group_by("launch_time").agg(pl.col("fuel_burn_kg").sum().alias("v"))
        .sort("launch_time").get_column("v").to_list()
    )
    m_ts = (
        m.group_by(cmap.get("launch_time", "launch_time"))
        .agg(pl.col(cmap.get("fuel_burn_kg", "fuel_burn_kg")).sum().alias("v"))
        .sort(cmap.get("launch_time", "launch_time")).get_column("v").to_list()
    )
    check("time-series trendline identical", o_ts == m_ts,
          f"{len(o_ts)} vs {len(m_ts)} points")

    # --- correlation matrix (analytical model equivalence) -----------------
    num = ["warhead_yield_kg", "sorties_flown", "kill_probability", "fuel_burn_kg"]
    o_corr = missions.select(num).corr().to_numpy()
    m_corr = m.select([cmap.get(c, c) for c in num]).corr().to_numpy()
    check("Pearson correlation matrix identical",
          bool((abs(o_corr - m_corr) < 1e-12).all()))

    # --- nullability topology ----------------------------------------------
    with_nulls = missions.with_columns(
        pl.when(pl.int_range(pl.len()) % 7 == 0)
        .then(None).otherwise(pl.col("callsign")).alias("callsign")
    )
    eng2 = OfflineIsomorphicEngine(TransformConfig(seed="null-test"))
    r2 = eng2.mask({"t": with_nulls})
    mc = r2.column_map.get("callsign", "callsign")
    check("null count preserved exactly",
          with_nulls.get_column("callsign").null_count()
          == r2.tables["t"].get_column(mc).null_count())

    # --- affine mode invertibility -----------------------------------------
    eng3 = OfflineIsomorphicEngine(TransformConfig(
        seed="affine", numeric_mode="affine", affine_scale=1.0,
        affine_offset=12.5, affine_geo_only=True,
    ))
    r3 = eng3.mask({"missions": missions})
    lat_m = r3.column_map.get("target_latitude", "target_latitude")
    shifted = r3.tables["missions"].get_column(lat_m)
    orig = missions.get_column("target_latitude")
    check("affine geo projection applied (y = x + 12.5)",
          abs(float(shifted[0]) - (float(orig[0]) + 12.5)) < 1e-9,
          f"{shifted[0]} vs {orig[0]}")
    back3 = OfflineIsomorphicEngine.restore(r3.tables, r3.mapping_payload)
    rec = back3.tables["missions"].get_column("target_latitude")
    check("affine projection exactly invertible",
          all(abs(float(a) - float(b)) < 1e-9 for a, b in zip(orig.to_list(), rec.to_list())))

    # --- non-geo measures untouched under geo-only affine ------------------
    fb = r3.column_map.get("fuel_burn_kg", "fuel_burn_kg")
    check("affine_geo_only leaves measures pristine",
          missions.get_column("fuel_burn_kg").sum()
          == r3.tables["missions"].get_column(fb).sum())


# --------------------------------------------------------------------------- #
#  G2b - Relational join topology across multiple tables
# --------------------------------------------------------------------------- #
def test_relational(tables: Dict[str, pl.DataFrame]) -> None:
    section("G2b RELATIONAL TOPOLOGY  (multi-table FK joins survive masking)")
    prof = SensitivityProfiler().profile_dataset(tables, "defense_db")
    fks = prof.foreign_keys
    check("foreign key detected (missions.base_id -> bases.base_id)",
          any(f["child_column"] == "base_id" and f["parent_table"] == "bases"
              for f in fks),
          str(fks))

    eng = OfflineIsomorphicEngine(TransformConfig(seed="rel-test"))
    res = eng.mask(tables)
    cmap = res.column_map

    o_join = (
        tables["missions"].join(tables["bases"], on="base_id", how="inner")
        .group_by("installation_name").agg(pl.len().alias("n"))
        .sort("n", "installation_name")
    )
    bid = cmap.get("base_id", "base_id")
    inst = cmap.get("installation_name", "installation_name")
    m_join = (
        res.tables["missions"].join(res.tables["bases"], on=bid, how="inner")
        .group_by(inst).agg(pl.len().alias("n"))
        .sort("n", inst)
    )
    check("inner-join cardinality preserved",
          o_join.height == m_join.height and o_join.get_column("n").to_list()
          == m_join.get_column("n").to_list(),
          f"{o_join.get_column('n').to_list()} vs {m_join.get_column('n').to_list()}")

    o_rows = tables["missions"].join(tables["bases"], on="base_id").height
    m_rows = res.tables["missions"].join(res.tables["bases"], on=bid).height
    check("join row count identical", o_rows == m_rows, f"{o_rows} vs {m_rows}")
    check("FK values consistently remapped across tables",
          set(res.tables["missions"].get_column(bid).unique().to_list())
          <= set(res.tables["bases"].get_column(bid).unique().to_list()))


# --------------------------------------------------------------------------- #
#  G3 - Determinism & bijectivity
# --------------------------------------------------------------------------- #
def test_bijectivity(missions: pl.DataFrame) -> None:
    section("G3  DETERMINISTIC BIJECTIVITY  (1 <-> 1)")
    a = OfflineIsomorphicEngine(TransformConfig(seed="fixed-seed-42"))
    b = OfflineIsomorphicEngine(TransformConfig(seed="fixed-seed-42"))
    ra, rb = a.mask({"m": missions}), b.mask({"m": missions})
    check("identical seed => byte-identical output",
          ra.tables["m"].equals(rb.tables["m"]))
    check("identical seed => identical column map", ra.column_map == rb.column_map)
    check("identical seed => identical value map",
          ra.mapping_payload["values"] == rb.mapping_payload["values"])

    c = OfflineIsomorphicEngine(TransformConfig(seed="different-seed-99"))
    rc = c.mask({"m": missions})
    check("different seed => different surrogates",
          ra.mapping_payload["values"] != rc.mapping_payload["values"])

    vals = ra.mapping_payload["values"]
    check("no many-to-one collisions in value map",
          len(set(vals.values())) == len(vals),
          f"{len(vals)} keys -> {len(set(vals.values()))} images")
    cols = ra.mapping_payload["columns"]
    check("no many-to-one collisions in column map",
          len(set(cols.values())) == len(cols))

    bm = BijectiveMap()
    bm.put("a", "X")
    try:
        bm.put("b", "X")
        check("BijectiveMap rejects duplicate image", False, "no exception")
    except EngineError:
        check("BijectiveMap rejects duplicate image", True)
    try:
        bm.put("a", "Y")
        check("BijectiveMap rejects key remap", False, "no exception")
    except EngineError:
        check("BijectiveMap rejects key remap", True)

    # Cardinality equality per masked column
    bad = []
    for oc in missions.columns:
        mc = ra.column_map.get(oc, oc)
        if missions.get_column(oc).n_unique() != ra.tables["m"].get_column(mc).n_unique():
            bad.append(oc)
    check("distinct cardinality preserved on every column", not bad, str(bad))


# --------------------------------------------------------------------------- #
#  G4 - Cryptographic vault
# --------------------------------------------------------------------------- #
def test_vault(missions: pl.DataFrame) -> None:
    section("G4  CRYPTOGRAPHIC VAULT  (.ciphermap)")
    eng = OfflineIsomorphicEngine(TransformConfig(seed="vault-test"))
    res = eng.mask({"missions": missions})
    vault = CipherVault(KDF_FAST)
    pw = "Corr3ct-Horse-Battery!"
    man = vault.seal(res.mapping_payload, pw, res.schema_fingerprint, "missions")

    for f in ("version", "cipher_suite", "salt", "nonce", "auth_tag",
              "schema_fingerprint", "encrypted_payload"):
        check(f"manifest field present: {f}", f in man)
    check("cipher suite is AES-256-GCM-Argon2id",
          man["cipher_suite"] == "AES-256-GCM-Argon2id")

    blob = str(man["encrypted_payload"]) + str(man)
    leaked = [
        s for s in ("strike_squadron", "TOP SECRET", "Target BASTION", "warhead")
        if s in blob
    ]
    check("no plaintext mapping leaks into the manifest", not leaked, str(leaked))

    out = vault.unseal(man, pw, res.schema_fingerprint)
    check("correct passphrase decrypts", out["values"] == res.mapping_payload["values"])

    try:
        vault.unseal(man, "WrongPassphrase!")
        check("wrong passphrase rejected", False, "decrypted anyway")
    except InvalidPassphrase:
        check("wrong passphrase rejected", True)

    try:
        vault.unseal(man, pw, "0" * 64)
        check("schema fingerprint mismatch rejected", False, "accepted")
    except SchemaMismatch:
        check("schema fingerprint mismatch rejected", True)

    import base64
    tampered = dict(man)
    raw = bytearray(base64.b64decode(str(man["encrypted_payload"])))
    raw[0] ^= 0xFF
    tampered["encrypted_payload"] = base64.b64encode(bytes(raw)).decode()
    try:
        vault.unseal(tampered, pw)
        check("ciphertext tampering detected", False, "accepted")
    except (InvalidPassphrase, TamperedVault):
        check("ciphertext tampering detected", True)

    hdr = dict(man)
    hdr["dataset_name"] = "innocuous"
    try:
        vault.unseal(hdr, pw)
        check("header (AAD) tampering detected", False, "accepted")
    except (InvalidPassphrase, TamperedVault):
        check("header (AAD) tampering detected", True)

    check("salt is 16 bytes", len(bytes.fromhex(str(man["salt"]))) == 16)
    check("nonce is 12 bytes", len(bytes.fromhex(str(man["nonce"]))) == 12)
    check("auth tag is 16 bytes", len(bytes.fromhex(str(man["auth_tag"]))) == 16)
    m2 = vault.seal(res.mapping_payload, pw, res.schema_fingerprint, "missions")
    check("salt/nonce are fresh per seal (semantic security)",
          m2["salt"] != man["salt"] and m2["nonce"] != man["nonce"])


# --------------------------------------------------------------------------- #
#  G5 - Lossless round-trip
# --------------------------------------------------------------------------- #
def test_roundtrip(tables: Dict[str, pl.DataFrame]) -> None:
    section("G5  LOSSLESS BIDIRECTIONAL ROUND-TRIP")
    eng = OfflineIsomorphicEngine(TransformConfig(seed="rt-test"))
    res = eng.mask(tables)
    vault = CipherVault(KDF_FAST)
    pw = "R0undTrip-Vault-2026!"
    man = vault.seal(res.mapping_payload, pw, res.schema_fingerprint, "defense_db")
    payload = vault.unseal(man, pw, res.schema_fingerprint)
    back = OfflineIsomorphicEngine.restore(res.tables, payload)

    for tname, odf in tables.items():
        rdf = back.tables.get(tname)
        if rdf is None:
            check(f"table restored: {tname}", False, "missing")
            continue
        check(f"[{tname}] column names restored", list(odf.columns) == list(rdf.columns),
              f"{list(rdf.columns)[:4]}")
        check(f"[{tname}] row count restored", odf.height == rdf.height)
        same = odf.equals(rdf)
        if not same:
            diffs = []
            for c in odf.columns:
                if c in rdf.columns and not odf.get_column(c).equals(rdf.get_column(c)):
                    diffs.append(c)
            check(f"[{tname}] EXACT value equality", False, f"differing: {diffs}")
        else:
            check(f"[{tname}] EXACT value equality", True)

    # Round-trip of a DOWNSTREAM ANALYTICAL OUTPUT (the hard requirement).
    cmap = res.column_map
    masked_report = (
        res.tables["missions"]
        .group_by(cmap.get("threat_level", "threat_level"))
        .agg(pl.col(cmap.get("sorties_flown", "sorties_flown")).sum().alias("total_sorties"))
        .sort("total_sorties")
    )
    restored_report = OfflineIsomorphicEngine.restore(
        {"missions": masked_report}, payload
    ).tables["missions"]
    original_report = (
        tables["missions"].group_by("threat_level")
        .agg(pl.col("sorties_flown").sum().alias("total_sorties"))
        .sort("total_sorties")
    )
    check("downstream BI aggregate re-identifies correctly",
          set(restored_report.get_column("threat_level").to_list())
          == set(original_report.get_column("threat_level").to_list()),
          f"{restored_report.get_column('threat_level').to_list()}")
    check("downstream aggregate values unchanged by re-identification",
          restored_report.get_column("total_sorties").to_list()
          == original_report.get_column("total_sorties").to_list())

    # Free-text narrative round-trip
    o_notes = tables["missions"].get_column("mission_notes").to_list()
    r_notes = back.tables["missions"].get_column("mission_notes").to_list()
    check("free-text narrative restored verbatim", o_notes == r_notes,
          next((f"{a!r} != {b!r}" for a, b in zip(o_notes, r_notes) if a != b), ""))


# --------------------------------------------------------------------------- #
#  Format fidelity
# --------------------------------------------------------------------------- #
def test_formats() -> None:
    section("FORMAT INGESTION & RE-SERIALISATION")
    ing = DataIngestor()
    writer = ArtifactWriter()

    r_csv = ing.load_path(os.path.join(SAMPLES, "classified_missions.csv"))
    check("CSV ingested", r_csv.primary.height == 420, str(r_csv.primary.height))

    r_pq = ing.load_path(os.path.join(SAMPLES, "classified_missions.parquet"))
    check("Parquet ingested", r_pq.primary.height == 420)

    r_xl = ing.load_path(os.path.join(SAMPLES, "classified_workbook.xlsx"))
    check("XLSX multi-sheet ingested (3 sheets)", len(r_xl.tables) == 3,
          str(list(r_xl.tables)))
    check("XLSX formula strings captured verbatim",
          any("=SUM" in f for sheet in r_xl.manifest.excel_formulas.values()
              for f in sheet.values()),
          str(r_xl.manifest.excel_formulas))

    r_sql = ing.load_path(os.path.join(SAMPLES, "classified_dump.sql"))
    check("SQL dump: COPY block parsed", r_sql.tables["bases"].height == 5,
          str(r_sql.tables["bases"].height))
    check("SQL dump: INSERT statements parsed",
          r_sql.tables["strike_log"].height == 40,
          str(r_sql.tables["strike_log"].height))
    check("SQL dump: DDL captured", "bases" in r_sql.manifest.sql_ddl)
    check("SQL dump: numeric types inferred",
          r_sql.tables["bases"].get_column("personnel_assigned").dtype == pl.Int64,
          str(r_sql.tables["bases"].get_column("personnel_assigned").dtype))

    eng = OfflineIsomorphicEngine(TransformConfig(seed="fmt"))
    res = eng.mask(r_xl.tables)
    xlsb, xname, xmime = writer.write(res.tables, r_xl.manifest, "excel",
                                      "masked_wb", res.table_name_map)
    check("XLSX re-serialised", len(xlsb) > 5000 and xname.endswith(".xlsx"))
    reread = ing.load_bytes(xlsb, xname)
    check("XLSX round-trips through writer -> reader",
          len(reread.tables) == 3, str(list(reread.tables)))

    sqlb, sname, _ = writer.write(res.tables, r_xl.manifest, "sql", "masked_db",
                                  res.table_name_map)
    check("SQL artifact emitted with DDL + INSERTs",
          b"CREATE TABLE" in sqlb and b"INSERT INTO" in sqlb)

    pqb, pname, _ = writer.write(
        {"missions": res.tables["Missions"]},
        r_csv.manifest, "parquet", "masked",
    )
    check("Parquet artifact emitted", len(pqb) > 1000)

    jb, jname, _ = writer.write(res.tables, r_xl.manifest, "json", "masked",
                                res.table_name_map)
    check("JSON artifact emitted", jb.strip().startswith(b"{"))

    # JSON multi-table ingestion
    r_json = ing.load_bytes(jb, "masked.json")
    check("JSON multi-table re-ingested", len(r_json.tables) == 3,
          str(list(r_json.tables)))


# --------------------------------------------------------------------------- #
#  Profiles & scale
# --------------------------------------------------------------------------- #
def test_profiles(missions: pl.DataFrame) -> None:
    section("DOMAIN PROFILES")
    from core.ontology import DOMAIN_PROFILES

    for key in DOMAIN_PROFILES:
        try:
            eng = OfflineIsomorphicEngine(TransformConfig(domain_profile=key, seed="p"))
            r = eng.mask({"m": missions.head(80)})
            back = OfflineIsomorphicEngine.restore(r.tables, r.mapping_payload)
            ok = back.tables["m"].equals(missions.head(80))
            check(f"profile '{key}' masks + restores losslessly", ok)
        except Exception as exc:
            check(f"profile '{key}' masks + restores losslessly", False,
                  f"{type(exc).__name__}: {exc}")


def test_scale() -> None:
    section("SCALE  (vectorised Polars path)")
    import time

    n = 200_000
    big = pl.DataFrame({
        "mission_id": [f"MSN-{i}" for i in range(n)],
        "strike_squadron": [f"{(i % 25) + 1}th Strike Squadron" for i in range(n)],
        "threat_level": [["LOW", "MEDIUM", "HIGH", "CRITICAL"][i % 4] for i in range(n)],
        "warhead_yield_kg": [(i % 97) * 11.5 for i in range(n)],
        "sorties_flown": [(i % 9) + 1 for i in range(n)],
    })
    t0 = time.time()
    eng = OfflineIsomorphicEngine(TransformConfig(seed="scale"))
    r = eng.mask({"big": big})
    dt = time.time() - t0
    check(f"200k x 5 masked in {dt:.2f}s", r.fidelity.passed and dt < 120,
          f"{dt:.2f}s")
    check("200k aggregate preserved",
          big.get_column("warhead_yield_kg").sum()
          == r.tables["big"].get_column(r.column_map["warhead_yield_kg"]).sum())
    t1 = time.time()
    back = OfflineIsomorphicEngine.restore(r.tables, r.mapping_payload)
    check(f"200k restored in {time.time() - t1:.2f}s", back.tables["big"].equals(big))


# --------------------------------------------------------------------------- #
def main() -> int:
    print("\033[1m" + "=" * 74)
    print("  AetherMask (CipherShift) :: Verification Suite")
    print("=" * 74 + "\033[0m")

    ing = DataIngestor()
    missions = ing.load_path(os.path.join(SAMPLES, "classified_missions.csv")).primary
    bases = ing.load_path(os.path.join(SAMPLES, "classified_bases.csv")).primary
    personnel = ing.load_path(os.path.join(SAMPLES, "classified_personnel.csv")).primary
    tables = {"missions": missions, "bases": bases, "personnel": personnel}

    for fn, args in (
        (test_airgap, (missions,)),
        (test_isomorphism, (missions,)),
        (test_relational, (tables,)),
        (test_bijectivity, (missions,)),
        (test_vault, (missions,)),
        (test_roundtrip, (tables,)),
        (test_formats, ()),
        (test_profiles, (missions,)),
        (test_scale, ()),
    ):
        try:
            fn(*args)
        except Exception:
            _FAILED.append(f"{fn.__name__} crashed")
            print(f"  \033[91mCRASH\033[0m {fn.__name__}")
            traceback.print_exc()

    total = len(_PASSED) + len(_FAILED)
    print("\n" + "=" * 74)
    if _FAILED:
        print(f"\033[91m  {len(_PASSED)}/{total} PASSED - {len(_FAILED)} FAILURE(S)\033[0m")
        for f in _FAILED:
            print(f"    - {f}")
        print("=" * 74)
        return 1
    print(f"\033[92m  ALL {total} CHECKS PASSED\033[0m")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
