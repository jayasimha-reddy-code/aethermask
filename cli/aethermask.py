#!/usr/bin/env python3
"""
AetherMask (CipherShift) :: offline command-line interface
==========================================================
For operators working on a terminal-only air-gapped host (no browser).

    aethermask profile    <input>
    aethermask obfuscate  <input> --passphrase-file pw.txt [--profile KEY]
    aethermask restore    <masked> <vault.ciphermap> --passphrase-file pw.txt
    aethermask verify     <original> <masked> <vault.ciphermap> --passphrase-file pw.txt
    aethermask attest

Passphrases are read from a file or an interactive prompt - never from argv,
so they cannot leak into shell history or the process table.
"""
from __future__ import annotations

import argparse
import getpass
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import polars as pl

from core.engine import OfflineIsomorphicEngine, TransformConfig
from core.ingest import DataIngestor, SourceManifest
from core.ontology import DOMAIN_PROFILES
from core.profiler import SensitivityProfiler
from core.security import CipherVault, VaultError
from core.serialize import ArtifactWriter

C_RESET, C_BOLD, C_GREEN, C_RED, C_CYAN, C_DIM = (
    "\033[0m", "\033[1m", "\033[92m", "\033[91m", "\033[96m", "\033[2m"
)


def _pass(args) -> str:
    if getattr(args, "passphrase_file", None):
        with open(args.passphrase_file, encoding="utf-8") as fh:
            pw = fh.read().strip()
        if not pw:
            sys.exit("Passphrase file is empty.")
        return pw
    pw = getpass.getpass("Vault passphrase: ")
    if len(pw) < 8:
        sys.exit("Passphrase must be at least 8 characters.")
    return pw


def cmd_profile(args) -> int:
    res = DataIngestor().load_path(args.input)
    ds = SensitivityProfiler(redact_values=True).profile_dataset(
        res.tables, res.manifest.dataset_name
    )
    if args.json:
        print(json.dumps(ds.to_dict(), indent=2))
        return 0
    print(f"\n{C_BOLD}Dataset:{C_RESET} {ds.dataset_name}")
    print(f"{C_BOLD}Risk:{C_RESET} {ds.risk_grade} ({ds.risk_score}/100)")
    print(f"{C_BOLD}Recommended profile:{C_RESET} {C_CYAN}{ds.recommended_profile}{C_RESET}")
    print(f"{C_BOLD}Findings:{C_RESET} {ds.finding_summary}")
    for t in ds.tables:
        print(f"\n  {C_BOLD}{t.name}{C_RESET}  {t.row_count} rows")
        print(f"  PK candidates: {t.primary_key_candidates or '-'}")
        print(f"  {'column':26s} {'dtype':11s} {'role':12s} {'distinct':>9s} {'sev':>4s}")
        print("  " + "-" * 68)
        for c in t.columns:
            sev = f"{C_RED}{c.max_severity}{C_RESET}" if c.max_severity >= 4 else str(c.max_severity)
            print(f"  {c.name[:26]:26s} {c.dtype[:11]:11s} {c.semantic_role[:12]:12s} "
                  f"{c.distinct_count:>9d} {sev:>4s}")
    if ds.foreign_keys:
        print(f"\n  {C_BOLD}Foreign keys{C_RESET}")
        for fk in ds.foreign_keys:
            print(f"    {fk['child_table']}.{fk['child_column']} -> "
                  f"{fk['parent_table']}.{fk['parent_column']}  ({fk['coverage']:.0%})")
    return 0


def cmd_obfuscate(args) -> int:
    pw = _pass(args)
    ing = DataIngestor()
    res = ing.load_path(args.input)
    profiler = SensitivityProfiler()
    profs = {t: profiler.profile_table(df, t) for t, df in res.tables.items()}

    cfg = TransformConfig(
        domain_profile=args.profile,
        numeric_mode=args.numeric_mode,
        affine_scale=args.affine_scale,
        affine_offset=args.affine_offset,
        seed=args.seed or os.urandom(16).hex(),
    )
    engine = OfflineIsomorphicEngine(cfg)
    mres = engine.mask(res.tables, profs, source_manifest=res.manifest.to_dict())

    outdir = args.outdir or os.path.dirname(os.path.abspath(args.input))
    os.makedirs(outdir, exist_ok=True)
    stem = f"{res.manifest.dataset_name}_sanitized"
    blob, fname, _ = ArtifactWriter().write(
        mres.tables, res.manifest, args.format, stem, mres.table_name_map
    )
    art_path = os.path.join(outdir, fname)
    with open(art_path, "wb") as fh:
        fh.write(blob)

    payload = dict(mres.mapping_payload)
    payload["artifact_sha256"] = CipherVault.content_digest(blob)
    vault = CipherVault()
    manifest = vault.seal(
        payload, pw, mres.schema_fingerprint, res.manifest.dataset_name,
        extra_header={"artifact_filename": fname,
                      "artifact_sha256": payload["artifact_sha256"]},
    )
    map_path = os.path.join(outdir, f"{res.manifest.dataset_name}.ciphermap")
    vault.write_manifest(manifest, map_path)

    fid = mres.fidelity.summary()
    mark = f"{C_GREEN}PASS{C_RESET}" if fid["passed"] else f"{C_RED}FAIL{C_RESET}"
    print(f"\n{C_BOLD}Obfuscation complete{C_RESET}")
    print(f"  profile     : {args.profile}")
    print(f"  artifact    : {art_path}  ({len(blob):,} bytes)")
    print(f"  vault       : {map_path}")
    print(f"  sha-256     : {payload['artifact_sha256']}")
    print(f"  headers     : {len(mres.column_map)} shifted")
    print(f"  tokens      : {mres.value_map_size:,} substituted")
    print(f"  isomorphism : {mark} ({fid['passed_checks']}/{fid['total_checks']} assertions)")
    if not fid["passed"]:
        for f in fid["failures"]:
            print(f"    - {f}")
        return 1
    print(f"\n{C_DIM}Store the .ciphermap and passphrase separately from the artifact.{C_RESET}")
    return 0


def cmd_restore(args) -> int:
    pw = _pass(args)
    manifest = CipherVault.read_manifest(args.ciphermap)
    vault = CipherVault()
    try:
        payload = vault.unseal(manifest, pw)
    except VaultError as exc:
        print(f"{C_RED}Vault error:{C_RESET} {exc}")
        return 2

    ing = DataIngestor()
    res = ing.load_path(args.masked)
    rres = OfflineIsomorphicEngine.restore(res.tables, payload, strict=args.strict)

    src = SourceManifest.from_dict(payload.get("source_manifest", {}))
    if not src.table_order:
        src.table_order = list(rres.tables.keys())
    outdir = args.outdir or os.path.dirname(os.path.abspath(args.masked))
    os.makedirs(outdir, exist_ok=True)
    stem = f"{src.dataset_name or 'dataset'}_restored"
    blob, fname, _ = ArtifactWriter().write(rres.tables, src, args.format, stem)
    path = os.path.join(outdir, fname)
    with open(path, "wb") as fh:
        fh.write(blob)

    print(f"\n{C_BOLD}Re-identification complete{C_RESET}")
    print(f"  output   : {path}  ({len(blob):,} bytes)")
    print(f"  tables   : {len(rres.tables)}")
    print(f"  rows     : {sum(df.height for df in rres.tables.values()):,}")
    print(f"  headers  : {rres.restored_columns} restored")
    print(f"  tokens   : {rres.restored_values:,} restored")
    return 0


def cmd_verify(args) -> int:
    pw = _pass(args)
    manifest = CipherVault.read_manifest(args.ciphermap)
    payload = CipherVault().unseal(manifest, pw)
    ing = DataIngestor()
    odf = ing.load_path(args.original).primary
    mdf = ing.load_path(args.masked).primary
    cmap = dict(payload.get("columns", {}))

    fails = 0
    print(f"\n{C_BOLD}Isomorphism audit{C_RESET}")
    def report(name: str, ok: bool, detail: str = "") -> None:
        nonlocal fails
        if not ok:
            fails += 1
        tag = f"{C_GREEN}PASS{C_RESET}" if ok else f"{C_RED}FAIL{C_RESET}"
        print(f"  [{tag}] {name} {C_DIM}{detail}{C_RESET}")

    report("row count", odf.height == mdf.height, f"{odf.height} vs {mdf.height}")
    report("column count", odf.width == mdf.width, f"{odf.width} vs {mdf.width}")
    for c in odf.columns:
        mc = cmap.get(c, c)
        if mc not in mdf.columns:
            report(f"column {c}", False, "absent from masked artifact")
            continue
        o, m = odf.get_column(c), mdf.get_column(mc)
        report(f"cardinality {c}", o.n_unique() == m.n_unique(),
               f"{o.n_unique()} vs {m.n_unique()}")
        report(f"nulls {c}", o.null_count() == m.null_count(),
               f"{o.null_count()} vs {m.null_count()}")
        if o.dtype.is_numeric() and m.dtype.is_numeric():
            report(f"sum {c}", OfflineIsomorphicEngine._num_eq(o.sum(), m.sum()),
                   f"{o.sum()} vs {m.sum()}")
    print(f"\n  {C_GREEN if not fails else C_RED}{'ALL CHECKS PASSED' if not fails else f'{fails} FAILURE(S)'}{C_RESET}")
    return 1 if fails else 0


def cmd_attest(args) -> int:
    from core.nlp import OfflineNER
    rep = {
        "product": "AetherMask (CipherShift) 1.0",
        "cryptography": CipherVault.backend_report(),
        "nlp": OfflineNER().describe(),
        "domain_profiles": sorted(DOMAIN_PROFILES),
        "polars": pl.__version__,
        "network_access": "none",
    }
    print(json.dumps(rep, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="aethermask",
        description="AetherMask (CipherShift) - offline semantic obfuscation toolkit",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("profile", help="Analyse schema and sensitivity")
    sp.add_argument("input")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_profile)

    so = sub.add_parser("obfuscate", help="Mask a dataset and emit a .ciphermap")
    so.add_argument("input")
    so.add_argument("--profile", default="defense_to_logistics", choices=sorted(DOMAIN_PROFILES))
    so.add_argument("--passphrase-file")
    so.add_argument("--outdir")
    so.add_argument("--format", default=None,
                    choices=[None, "csv", "tsv", "excel", "parquet", "json", "ndjson", "sql"])
    so.add_argument("--numeric-mode", default="identity", choices=["identity", "affine"])
    so.add_argument("--affine-scale", type=float, default=1.0)
    so.add_argument("--affine-offset", type=float, default=0.0)
    so.add_argument("--seed", default=None)
    so.set_defaults(func=cmd_obfuscate)

    sr = sub.add_parser("restore", help="Re-identify a masked dataset")
    sr.add_argument("masked")
    sr.add_argument("ciphermap")
    sr.add_argument("--passphrase-file")
    sr.add_argument("--outdir")
    sr.add_argument("--format", default=None,
                    choices=[None, "csv", "tsv", "excel", "parquet", "json", "ndjson", "sql"])
    sr.add_argument("--strict", action="store_true")
    sr.set_defaults(func=cmd_restore)

    sv = sub.add_parser("verify", help="Audit isomorphism of an original/masked pair")
    sv.add_argument("original")
    sv.add_argument("masked")
    sv.add_argument("ciphermap")
    sv.add_argument("--passphrase-file")
    sv.set_defaults(func=cmd_verify)

    sa = sub.add_parser("attest", help="Print the air-gap / crypto attestation")
    sa.set_defaults(func=cmd_attest)
    return p


def main() -> int:
    args = build_parser().parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
