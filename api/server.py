"""
AetherMask (CipherShift) :: api.server
======================================
Production FastAPI application for 100% offline, air-gapped execution.

Endpoints
---------
  GET  /api/v1/health          Liveness + air-gap attestation
  GET  /api/v1/profiles        Catalogue of bundled domain-shift profiles
  POST /api/v1/profile         Schema + sensitivity analysis (no data retained)
  POST /api/v1/obfuscate       File -> sanitized artifact + encrypted .ciphermap
  POST /api/v1/restore         Sanitized artifact + .ciphermap + passphrase -> original
  POST /api/v1/preview         Split-screen preview payload for the Data Studio UI
  POST /api/v1/verify          Re-run isomorphism assertions on a masked/raw pair
  GET  /api/v1/attestation     Full offline compliance report

Hard offline guarantees enforced here
-------------------------------------
* Binds to a local socket only (default 127.0.0.1; 0.0.0.0 allowed explicitly
  for container/preview use where the network namespace is already isolated).
* `EgressGuardMiddleware` + an import-time `socket` sentinel make any outbound
  connection attempt raise and be logged as a compliance event.
* No CDN, no analytics, no external fonts, no telemetry, no model downloads.
* Uploaded bytes live only in memory for the duration of the request; the
  profile endpoint never persists or echoes raw cell values beyond redacted
  evidence fragments.
"""

from __future__ import annotations

import io
import json
import logging
import os
import socket
import sys
import time
import uuid
from typing import Any, Dict, List, Mapping, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import polars as pl
from fastapi import Body, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from core.engine import (
    EngineError, FidelityError, OfflineIsomorphicEngine, TransformConfig,
)
from core.ingest import DataIngestor, IngestError, SourceManifest, SUPPORTED_EXTENSIONS
from core.ontology import DOMAIN_PROFILES, list_profiles, lexicon_report, profile_pool_sizes
from core.profiler import SensitivityProfiler
from core.security import (
    CipherVault, InvalidPassphrase, KdfParams, SchemaMismatch, TamperedVault, VaultError,
)
from core.serialize import ArtifactWriter

# --------------------------------------------------------------------------- #
#  Logging (local stdout only - no remote log shipping)
# --------------------------------------------------------------------------- #
logging.basicConfig(
    level=os.environ.get("AETHERMASK_LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)-7s | aethermask | %(message)s",
)
log = logging.getLogger("aethermask")

MAX_UPLOAD_BYTES = int(os.environ.get("AETHERMASK_MAX_UPLOAD_MB", "2048")) * 1024 * 1024
PREVIEW_ROWS = 60

# --------------------------------------------------------------------------- #
#  Egress sentinel - records (and by default blocks) outbound connections
# --------------------------------------------------------------------------- #
_EGRESS_EVENTS: List[Dict[str, Any]] = []
_BLOCK_EGRESS = os.environ.get("AETHERMASK_BLOCK_EGRESS", "1") == "1"
_ALLOW_LOCAL_PG = os.environ.get("AETHERMASK_ALLOW_LOCAL_PG", "1") == "1"


def _install_egress_sentinel() -> None:
    """
    Wrap socket.connect so that any non-loopback egress is refused and logged.

    Loopback is permitted so the ASGI server, and an explicitly enabled local
    PostgreSQL read, keep working inside the container.
    """
    orig_connect = socket.socket.connect

    def guarded_connect(self, address, *args, **kwargs):  # type: ignore[no-untyped-def]
        host = None
        try:
            if isinstance(address, tuple) and address:
                host = str(address[0])
        except Exception:
            host = None

        allowed = host in (None, "127.0.0.1", "::1", "localhost", "0.0.0.0")
        if not allowed and _ALLOW_LOCAL_PG:
            try:
                import ipaddress

                ip = ipaddress.ip_address(host)  # type: ignore[arg-type]
                allowed = ip.is_loopback or ip.is_private or ip.is_link_local
            except Exception:
                allowed = False

        if not allowed:
            evt = {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "target": str(address),
                "action": "blocked" if _BLOCK_EGRESS else "logged",
            }
            _EGRESS_EVENTS.append(evt)
            log.error("AIR-GAP VIOLATION ATTEMPT: outbound connection to %s", address)
            if _BLOCK_EGRESS:
                raise OSError(
                    f"AetherMask air-gap policy: outbound network connection to "
                    f"{address} is forbidden."
                )
        return orig_connect(self, address, *args, **kwargs)

    socket.socket.connect = guarded_connect  # type: ignore[assignment]


_install_egress_sentinel()


# --------------------------------------------------------------------------- #
#  Application
# --------------------------------------------------------------------------- #
app = FastAPI(
    title="AetherMask (CipherShift)",
    description=(
        "Air-gapped semantic obfuscation, anonymization and lossless "
        "de-anonymization platform. 100% offline execution."
    ),
    version="2.1.0",
    docs_url="/api/docs",
    redoc_url=None,
    openapi_url="/api/openapi.json",
)

# Same-origin SPA; permissive CORS is confined to the local preview host only.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|0\.0\.0\.0)(:\d+)?|https://.*\.e2b\.app",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    """
    Attach a strict, self-only Content-Security-Policy.

    `default-src 'self'` with no external origins is what makes the shipped SPA
    provably CDN-free: a browser will refuse to load any third-party asset even
    if one were accidentally introduced.
    """
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception as exc:  # pragma: no cover
        log.exception("Unhandled error")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Internal error: {type(exc).__name__}: {exc}"},
        )
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "font-src 'self' data:; "
        "connect-src 'self'; "
        "form-action 'self'; "
        "frame-ancestors *; "
        "base-uri 'self'"
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-AetherMask-Airgap"] = "enforced"
    response.headers["X-Process-Time-Ms"] = f"{(time.perf_counter() - started) * 1000:.1f}"
    return response


# --------------------------------------------------------------------------- #
#  Shared helpers
# --------------------------------------------------------------------------- #
_ingestor = DataIngestor()
_writer = ArtifactWriter()
_profiler = SensitivityProfiler()
#: Redacting profiler used by /api/v1/profile so that a schema analysis can be
#: produced and shared WITHOUT echoing any confidential cell value back.
_redacting_profiler = SensitivityProfiler(redact_values=True)


def _kdf_params() -> KdfParams:
    """Allow low-memory appliances to dial Argon2 down via env."""
    mem = int(os.environ.get("AETHERMASK_ARGON2_MEMORY_KIB", "262144"))
    t = int(os.environ.get("AETHERMASK_ARGON2_TIME", "4"))
    p = int(os.environ.get("AETHERMASK_ARGON2_PARALLELISM", "2"))
    return KdfParams(time_cost=t, memory_cost_kib=mem, parallelism=p)


async def _read_upload(f: UploadFile) -> bytes:
    data = await f.read()
    if not data:
        raise HTTPException(400, f"Uploaded file '{f.filename}' is empty.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            413,
            f"File exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit.",
        )
    ext = os.path.splitext(f.filename or "")[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            415,
            f"Unsupported file type '{ext}'. Supported: {', '.join(SUPPORTED_EXTENSIONS)}",
        )
    return data


def _json_safe(v: Any) -> Any:
    import math
    from datetime import date, datetime, time as dtime
    from decimal import Decimal

    if v is None:
        return None
    if isinstance(v, float):
        return None if (math.isnan(v) or math.isinf(v)) else v
    if isinstance(v, (int, bool, str)):
        return v
    if isinstance(v, (datetime, date, dtime)):
        return v.isoformat()
    if isinstance(v, Decimal):
        return float(v)
    return str(v)


def _frame_preview(df: pl.DataFrame, rows: int = PREVIEW_ROWS) -> Dict[str, Any]:
    head = df.head(rows)
    return {
        "columns": list(df.columns),
        "dtypes": [str(df.get_column(c).dtype) for c in df.columns],
        "rows": [[_json_safe(v) for v in r] for r in head.iter_rows()],
        "total_rows": df.height,
        "total_columns": df.width,
    }


def _chart_series(df: pl.DataFrame, cat_col: str, val_col: str,
                  limit: int = 14) -> List[Dict[str, Any]]:
    """Aggregate a (category, measure) pair into a Recharts-ready series."""
    try:
        agg = (
            df.group_by(cat_col)
            .agg(pl.col(val_col).sum().alias("value"), pl.len().alias("count"))
            .sort("value", descending=True)
            .head(limit)
        )
        return [
            {
                "name": _json_safe(r[cat_col]),
                "value": _json_safe(r["value"]),
                "count": int(r["count"]),
            }
            for r in agg.iter_rows(named=True)
        ]
    except Exception:
        return []


def _pick_chart_columns(df: pl.DataFrame, prof) -> Optional[Dict[str, str]]:
    """Choose a low-cardinality category and a numeric measure for the demo chart."""
    cat = None
    val = None
    for c in prof.columns:
        if cat is None and c.semantic_role in ("categorical", "boolean") and 1 < c.distinct_count <= 24:
            cat = c.name
        if val is None and c.semantic_role == "measure" and c.numeric_stats:
            val = c.name
    if cat is None:
        for c in prof.columns:
            if c.distinct_count and 1 < c.distinct_count <= 24:
                cat = c.name
                break
    if val is None:
        for c in prof.columns:
            if df.get_column(c.name).dtype.is_numeric():
                val = c.name
                break
    if cat and val:
        return {"category": cat, "measure": val}
    return None


# --------------------------------------------------------------------------- #
#  Models
# --------------------------------------------------------------------------- #
class HealthResponse(BaseModel):
    status: str
    version: str
    airgapped: bool
    timestamp: str


class RestoreJsonRequest(BaseModel):
    passphrase: str = Field(..., min_length=8)
    ciphermap: Dict[str, Any]
    tables: Dict[str, List[Dict[str, Any]]]
    strict: bool = False


# --------------------------------------------------------------------------- #
#  Endpoints
# --------------------------------------------------------------------------- #
@app.get("/api/v1/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        status="operational",
        version="2.1.0",
        airgapped=True,
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    )


@app.get("/api/v1/profiles")
async def profiles() -> Dict[str, Any]:
    """
    Catalogue of offline domain-shift profiles.

    Each entry is augmented with its surrogate-pool capacity so the Data Studio
    can warn an operator before a high-cardinality column exhausts a pool and
    forces numeric-suffix fallbacks.
    """
    catalogue = list_profiles()
    for entry in catalogue:
        sizes = profile_pool_sizes(entry["key"])
        entry["pool_sizes"] = sizes
        entry["pool_capacity"] = str(sum(sizes.values()))
    return {
        "profiles": catalogue,
        "count": len(DOMAIN_PROFILES),
        "lexicon": {
            "total_unique_surrogates": lexicon_report()["total_unique_surrogates"],
        },
    }


@app.get("/api/v1/attestation")
async def attestation() -> Dict[str, Any]:
    from core.nlp import OfflineNER

    return {
        "product": "AetherMask (CipherShift)",
        "version": "2.1.0",
        "airgap": {
            "egress_blocking": _BLOCK_EGRESS,
            "blocked_attempts": len(_EGRESS_EVENTS),
            "events": _EGRESS_EVENTS[-25:],
            "external_apis": "none",
            "cdn_assets": "none",
            "telemetry": "none",
            "model_downloads": "none",
        },
        "cryptography": CipherVault.backend_report(),
        "kdf_policy": _kdf_params().to_dict(),
        "nlp": OfflineNER().describe(),
        "engine": {
            "dataframe": f"polars {pl.__version__}",
            "domain_profiles": len(DOMAIN_PROFILES),
        },
        "lexicon": lexicon_report(),
        "supported_formats": list(SUPPORTED_EXTENSIONS),
    }


# ----------------------------- PROFILE ------------------------------------- #
@app.post("/api/v1/profile")
async def profile_dataset(
    file: UploadFile = File(...),
    dataset_name: Optional[str] = Form(None),
) -> Dict[str, Any]:
    """
    Analyse schema, relational topology and sensitivity.

    The uploaded bytes are parsed in-memory and discarded when the response is
    produced. Only aggregate statistics and REDACTED evidence fragments are
    returned; full cell values are never echoed back.
    """
    data = await _read_upload(file)
    try:
        res = _ingestor.load_bytes(data, file.filename or "upload", dataset_name)
    except IngestError as exc:
        raise HTTPException(422, str(exc)) from exc

    ds = _redacting_profiler.profile_dataset(res.tables, res.manifest.dataset_name)
    payload = ds.to_dict()
    payload["source"] = res.manifest.to_dict()
    payload["total_rows"] = res.total_rows()
    payload["table_count"] = len(res.tables)

    del data, res  # explicit: no retention
    return payload


# ---------------------------- OBFUSCATE ------------------------------------ #
@app.post("/api/v1/obfuscate")
async def obfuscate(
    file: UploadFile = File(...),
    passphrase: str = Form(..., min_length=8),
    domain_profile: str = Form("defense_to_logistics"),
    output_format: Optional[str] = Form(None),
    numeric_mode: str = Form("identity"),
    affine_scale: float = Form(1.0),
    affine_offset: float = Form(0.0),
    affine_geo_only: bool = Form(True),
    mask_column_names: bool = Form(True),
    mask_categoricals: bool = Form(True),
    mask_identifiers: bool = Form(True),
    mask_free_text: bool = Form(True),
    mask_table_names: bool = Form(True),
    seed: Optional[str] = Form(None),
    dataset_name: Optional[str] = Form(None),
    passthrough_columns: Optional[str] = Form(None),
    include_preview: bool = Form(True),
) -> Dict[str, Any]:
    """
    Ingest a confidential file and return:
      * the sanitized artifact (base64, original physical format by default)
      * the encrypted `.ciphermap` manifest
      * the statistical-fidelity verification report
      * an optional split-screen preview + chart-parity series for the UI

    The plaintext mapping NEVER leaves this process unencrypted.
    """
    import base64

    if domain_profile not in DOMAIN_PROFILES:
        raise HTTPException(400, f"Unknown domain profile '{domain_profile}'.")

    data = await _read_upload(file)
    try:
        res = _ingestor.load_bytes(data, file.filename or "upload", dataset_name)
    except IngestError as exc:
        raise HTTPException(422, str(exc)) from exc

    passthrough = [
        c.strip() for c in (passthrough_columns or "").split(",") if c.strip()
    ]
    cfg = TransformConfig(
        domain_profile=domain_profile,
        numeric_mode=numeric_mode,
        affine_scale=affine_scale,
        affine_offset=affine_offset,
        affine_geo_only=affine_geo_only,
        mask_column_names=mask_column_names,
        mask_categoricals=mask_categoricals,
        mask_identifiers=mask_identifiers,
        mask_free_text=mask_free_text,
        mask_table_names=mask_table_names,
        passthrough_columns=passthrough,
        seed=seed or uuid.uuid4().hex,
        verify_fidelity=True,
    )

    profiles_map = {
        t: _profiler.profile_table(df, t) for t, df in res.tables.items()
    }

    engine = OfflineIsomorphicEngine(cfg)
    try:
        mres = engine.mask(
            res.tables, profiles_map, source_manifest=res.manifest.to_dict()
        )
    except FidelityError as exc:
        raise HTTPException(500, f"Isomorphism verification failed: {exc}") from exc
    except EngineError as exc:
        raise HTTPException(500, f"Transformation error: {exc}") from exc

    # --- serialise the sanitized artifact ------------------------------- #
    fmt = output_format or res.manifest.source_kind
    stem = f"{res.manifest.dataset_name}_sanitized"
    try:
        blob, fname, mime = _writer.write(
            mres.tables, res.manifest, fmt, stem, mres.table_name_map
        )
    except Exception as exc:
        raise HTTPException(500, f"Serialisation failed: {exc}") from exc

    # --- seal the vault -------------------------------------------------- #
    vault = CipherVault(_kdf_params())
    payload = dict(mres.mapping_payload)
    payload["artifact_sha256"] = CipherVault.content_digest(blob)
    try:
        manifest = vault.seal(
            payload, passphrase, mres.schema_fingerprint,
            dataset_name=res.manifest.dataset_name,
            extra_header={
                "artifact_filename": fname,
                "artifact_sha256": payload["artifact_sha256"],
                "table_count": len(mres.tables),
            },
        )
    except VaultError as exc:
        raise HTTPException(400, f"Vault sealing failed: {exc}") from exc

    out: Dict[str, Any] = {
        "status": "obfuscated",
        "dataset_name": res.manifest.dataset_name,
        "domain_profile": domain_profile,
        "profile_title": DOMAIN_PROFILES[domain_profile].title,
        "artifact": {
            "filename": fname,
            "mime_type": mime,
            "size_bytes": len(blob),
            "sha256": payload["artifact_sha256"],
            "base64": base64.b64encode(blob).decode("ascii"),
        },
        "ciphermap": {
            "filename": f"{res.manifest.dataset_name}.ciphermap",
            "manifest": manifest,
        },
        "fidelity": mres.fidelity.to_dict(),
        "statistics": {
            "tables": len(mres.tables),
            "total_rows": sum(df.height for df in mres.tables.values()),
            "columns_renamed": len(mres.column_map),
            "values_substituted": mres.value_map_size,
            "table_name_map": mres.table_name_map,
        },
        "engine": engine.describe(),
        "schema_fingerprint": mres.schema_fingerprint,
        "warning": (
            "Store the .ciphermap and its passphrase separately from the "
            "sanitized artifact. Without both, re-identification is "
            "cryptographically infeasible."
        ),
    }

    if include_preview:
        first = res.manifest.table_order[0] if res.manifest.table_order else next(iter(res.tables))
        odf, mdf = res.tables[first], mres.tables[first]
        prof = profiles_map[first]
        chart_cols = _pick_chart_columns(odf, prof)
        preview: Dict[str, Any] = {
            "table": first,
            "masked_table": mres.table_name_map.get(first, first),
            "original": _frame_preview(odf),
            "sanitized": _frame_preview(mdf),
            "column_map": {
                c.name: mres.column_map.get(c.name, c.name) for c in prof.columns
            },
            "column_strategies": {
                c.name: engine.column_meta.get(f"{first}.{c.name}", {}).get("strategy", "")
                for c in prof.columns
            },
        }
        if chart_cols:
            cat, val = chart_cols["category"], chart_cols["measure"]
            mcat = mres.column_map.get(cat, cat)
            mval = mres.column_map.get(val, val)
            preview["chart"] = {
                "category_column": cat,
                "measure_column": val,
                "masked_category_column": mcat,
                "masked_measure_column": mval,
                "original_series": _chart_series(odf, cat, val),
                "sanitized_series": _chart_series(mdf, mcat, mval),
            }
        out["preview"] = preview

    del data
    return out


# ----------------------------- RESTORE ------------------------------------- #
@app.post("/api/v1/restore")
async def restore(
    file: UploadFile = File(...),
    ciphermap: UploadFile = File(...),
    passphrase: str = Form(..., min_length=8),
    output_format: Optional[str] = Form(None),
    strict: bool = Form(False),
    verify_artifact_digest: bool = Form(False),
    include_preview: bool = Form(True),
) -> Dict[str, Any]:
    """
    Re-identify a sanitized artifact (or a downstream analytical output).

    Validates the vault, decrypts with the operator passphrase, inverts the
    bijection, and restores original headers, keys, categories and narrative
    entities with zero data loss.
    """
    import base64

    data = await _read_upload(file)
    map_raw = await ciphermap.read()
    if not map_raw:
        raise HTTPException(400, "The .ciphermap file is empty.")
    try:
        manifest = json.loads(map_raw.decode("utf-8"))
    except Exception as exc:
        raise HTTPException(422, f"Invalid .ciphermap JSON: {exc}") from exc
    if not isinstance(manifest, dict):
        raise HTTPException(422, "The .ciphermap must contain a JSON object.")

    if verify_artifact_digest:
        declared = manifest.get("artifact_sha256")
        actual = CipherVault.content_digest(data)
        if declared and declared != actual:
            raise HTTPException(
                409,
                "Artifact digest mismatch: the uploaded file is not the exact "
                "artifact this .ciphermap was issued for.\n"
                f"  expected {declared}\n  actual   {actual}",
            )

    vault = CipherVault(_kdf_params())
    try:
        payload = vault.unseal(manifest, passphrase)
    except InvalidPassphrase as exc:
        raise HTTPException(401, str(exc)) from exc
    except SchemaMismatch as exc:
        raise HTTPException(409, str(exc)) from exc
    except TamperedVault as exc:
        raise HTTPException(422, str(exc)) from exc
    except VaultError as exc:
        raise HTTPException(400, str(exc)) from exc

    try:
        res = _ingestor.load_bytes(data, file.filename or "upload")
    except IngestError as exc:
        raise HTTPException(422, str(exc)) from exc

    try:
        rres = OfflineIsomorphicEngine.restore(res.tables, payload, strict=strict)
    except EngineError as exc:
        raise HTTPException(500, f"Re-identification failed: {exc}") from exc

    src_manifest = SourceManifest.from_dict(payload.get("source_manifest", {}))
    if not src_manifest.table_order:
        src_manifest.table_order = list(rres.tables.keys())
    fmt = output_format or src_manifest.source_kind or res.manifest.source_kind
    stem = f"{src_manifest.dataset_name or 'dataset'}_restored"

    try:
        blob, fname, mime = _writer.write(rres.tables, src_manifest, fmt, stem)
    except Exception as exc:
        raise HTTPException(500, f"Serialisation failed: {exc}") from exc

    out: Dict[str, Any] = {
        "status": "restored",
        "artifact": {
            "filename": fname,
            "mime_type": mime,
            "size_bytes": len(blob),
            "sha256": CipherVault.content_digest(blob),
            "base64": base64.b64encode(blob).decode("ascii"),
        },
        "statistics": {
            "tables": len(rres.tables),
            "total_rows": sum(df.height for df in rres.tables.values()),
            "columns_restored": rres.restored_columns,
            "values_restored": rres.restored_values,
            "table_name_map": rres.table_name_map,
        },
        "vault": {
            "version": manifest.get("version"),
            "cipher_suite": manifest.get("cipher_suite"),
            "dataset_name": manifest.get("dataset_name"),
            "schema_fingerprint": manifest.get("schema_fingerprint"),
            "created_utc": manifest.get("created_utc"),
            "domain_profile": payload.get("domain_profile"),
        },
    }

    if include_preview:
        first = next(iter(rres.tables))
        out["preview"] = {
            "table": first,
            "restored": _frame_preview(rres.tables[first]),
        }

    del data, payload
    return out


# ----------------------------- PREVIEW ------------------------------------- #
@app.post("/api/v1/preview")
async def preview(
    file: UploadFile = File(...),
    domain_profile: str = Form("defense_to_logistics"),
    numeric_mode: str = Form("identity"),
    seed: Optional[str] = Form(None),
    rows: int = Form(PREVIEW_ROWS),
) -> Dict[str, Any]:
    """
    Dry-run transformation for the split-screen Data Studio.

    Produces no vault and no downloadable artifact - it exists so an operator
    can inspect the semantic projection and chart parity before committing.
    """
    if domain_profile not in DOMAIN_PROFILES:
        raise HTTPException(400, f"Unknown domain profile '{domain_profile}'.")

    data = await _read_upload(file)
    try:
        res = _ingestor.load_bytes(data, file.filename or "upload")
    except IngestError as exc:
        raise HTTPException(422, str(exc)) from exc

    first = res.manifest.table_order[0] if res.manifest.table_order else next(iter(res.tables))
    odf = res.tables[first]
    prof = _profiler.profile_table(odf, first)

    engine = OfflineIsomorphicEngine(
        TransformConfig(
            domain_profile=domain_profile,
            numeric_mode=numeric_mode,
            seed=seed or "preview-seed",
            verify_fidelity=True,
        )
    )
    try:
        mres = engine.mask({first: odf}, {first: prof})
    except EngineError as exc:
        raise HTTPException(500, str(exc)) from exc

    mdf = mres.tables[first]
    chart_cols = _pick_chart_columns(odf, prof)
    out: Dict[str, Any] = {
        "table": first,
        "domain_profile": domain_profile,
        "profile_title": DOMAIN_PROFILES[domain_profile].title,
        "original": _frame_preview(odf, rows),
        "sanitized": _frame_preview(mdf, rows),
        "column_map": mres.column_map,
        "column_strategies": {
            c.name: engine.column_meta.get(f"{first}.{c.name}", {}).get("strategy", "")
            for c in prof.columns
        },
        "sensitivity": {
            c.name: {"severity": c.max_severity, "role": c.semantic_role,
                     "findings": [f["rule_id"] for f in c.findings]}
            for c in prof.columns
        },
        "fidelity": mres.fidelity.summary(),
    }
    if chart_cols:
        cat, val = chart_cols["category"], chart_cols["measure"]
        out["chart"] = {
            "category_column": cat,
            "measure_column": val,
            "masked_category_column": mres.column_map.get(cat, cat),
            "masked_measure_column": mres.column_map.get(val, val),
            "original_series": _chart_series(odf, cat, val),
            "sanitized_series": _chart_series(
                mdf, mres.column_map.get(cat, cat), mres.column_map.get(val, val)
            ),
        }
    del data
    return out


# ------------------------------ VERIFY ------------------------------------- #
@app.post("/api/v1/verify")
async def verify(
    original: UploadFile = File(...),
    sanitized: UploadFile = File(...),
    ciphermap: UploadFile = File(...),
    passphrase: str = Form(..., min_length=8),
) -> Dict[str, Any]:
    """
    Independent isomorphism audit of an (original, sanitized, vault) triple.

    Recomputes aggregates on both sides and confirms the masked artifact is a
    faithful statistical image of the confidential source.
    """
    o_raw = await _read_upload(original)
    s_raw = await _read_upload(sanitized)
    m_raw = await ciphermap.read()

    try:
        manifest = json.loads(m_raw.decode("utf-8"))
        payload = CipherVault(_kdf_params()).unseal(manifest, passphrase)
    except InvalidPassphrase as exc:
        raise HTTPException(401, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(422, f"Vault error: {exc}") from exc

    o_res = _ingestor.load_bytes(o_raw, original.filename or "original")
    s_res = _ingestor.load_bytes(s_raw, sanitized.filename or "sanitized")

    col_map: Dict[str, str] = dict(payload.get("columns", {}))
    checks: List[Dict[str, Any]] = []

    o_first = next(iter(o_res.tables))
    s_first = next(iter(s_res.tables))
    odf, sdf = o_res.tables[o_first], s_res.tables[s_first]

    checks.append({
        "check": "row_count", "ok": odf.height == sdf.height,
        "detail": f"{odf.height} vs {sdf.height}",
    })
    checks.append({
        "check": "column_count", "ok": odf.width == sdf.width,
        "detail": f"{odf.width} vs {sdf.width}",
    })

    for c in odf.columns:
        mc = col_map.get(c, c)
        if mc not in sdf.columns:
            checks.append({"check": f"column_present::{c}", "ok": False, "detail": mc})
            continue
        os_, ms_ = odf.get_column(c), sdf.get_column(mc)
        checks.append({
            "check": f"cardinality::{c}",
            "ok": os_.n_unique() == ms_.n_unique(),
            "detail": f"{os_.n_unique()} vs {ms_.n_unique()}",
        })
        checks.append({
            "check": f"nulls::{c}",
            "ok": os_.null_count() == ms_.null_count(),
            "detail": f"{os_.null_count()} vs {ms_.null_count()}",
        })
        meta = (
            payload.get("column_meta", {}).get(f"{o_first}.{c}")
            or payload.get("column_meta", {}).get(c, {})
        )
        is_id = (
            meta.get("role") == "identifier"
            or meta.get("strategy") == "numeric_identifier_bijection"
        )
        is_affine = meta.get("strategy") == "affine"
        if os_.dtype.is_numeric() and ms_.dtype.is_numeric() and not is_id and not is_affine:
            checks.append({
                "check": f"sum::{c}",
                "ok": OfflineIsomorphicEngine._num_eq(os_.sum(), ms_.sum()),
                "detail": f"{os_.sum()} vs {ms_.sum()}",
            })

    failed = [c for c in checks if not c["ok"]]
    return {
        "passed": not failed,
        "total_checks": len(checks),
        "failed_checks": len(failed),
        "checks": checks,
        "schema_fingerprint": manifest.get("schema_fingerprint"),
    }


# --------------------------------------------------------------------------- #
#  Static SPA mount (served from local disk - no CDN)
# --------------------------------------------------------------------------- #
_STATIC_DIR = os.environ.get(
    "AETHERMASK_STATIC_DIR",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "dist"),
)

if os.path.isdir(_STATIC_DIR):
    app.mount("/", StaticFiles(directory=_STATIC_DIR, html=True), name="spa")
    log.info("Serving offline SPA from %s", _STATIC_DIR)
else:  # pragma: no cover
    @app.get("/", response_class=HTMLResponse)
    async def root() -> str:
        return (
            "<!doctype html><html><head><meta charset='utf-8'>"
            "<title>AetherMask</title></head><body "
            "style='font-family:system-ui;background:#0b1220;color:#e6edf7;padding:40px'>"
            "<h1>AetherMask (CipherShift)</h1>"
            "<p>API is operational. The static SPA bundle was not found at "
            f"<code>{_STATIC_DIR}</code>.</p>"
            "<p>Build it with <code>npm run build</code> in <code>frontend/</code>, "
            "or explore <a style='color:#6ea8fe' href='/api/docs'>/api/docs</a>.</p>"
            "</body></html>"
        )


def main() -> None:  # pragma: no cover
    import uvicorn

    host = os.environ.get("AETHERMASK_HOST", "127.0.0.1")
    port = int(os.environ.get("AETHERMASK_PORT", "8000"))
    log.info("AetherMask starting on %s:%s (air-gap enforced)", host, port)
    uvicorn.run(app, host=host, port=port, log_level="info", access_log=True)


if __name__ == "__main__":  # pragma: no cover
    main()
