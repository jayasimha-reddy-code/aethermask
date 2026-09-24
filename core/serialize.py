"""
AetherMask (CipherShift) :: core.serialize
==========================================
Faithful re-emission of tables into the source's physical format.

`ArtifactWriter.write(tables, manifest, fmt)` returns `(bytes, filename, mime)`.

Format fidelity
---------------
csv     : original delimiter restored from the manifest
excel   : every sheet recreated in original order; captured formula strings are
          re-applied to their exact cells; column widths auto-fitted
parquet : columnar round-trip through Polars/PyArrow
json    : original root shape (records vs table map vs ndjson) preserved
sql     : emits CREATE TABLE DDL (rewritten to the masked identifiers) plus
          parameter-safe INSERT statements with correct SQL literal quoting

None of these paths touch the network.
"""

from __future__ import annotations

import io
import json
import math
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import polars as pl

from .ingest import SourceManifest

__all__ = ["ArtifactWriter", "MIME_TYPES"]

MIME_TYPES: Dict[str, str] = {
    "csv": "text/csv",
    "tsv": "text/tab-separated-values",
    "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "parquet": "application/vnd.apache.parquet",
    "json": "application/json",
    "ndjson": "application/x-ndjson",
    "sql": "application/sql",
}

_EXTENSIONS: Dict[str, str] = {
    "csv": ".csv", "tsv": ".tsv", "excel": ".xlsx",
    "parquet": ".parquet", "json": ".json", "ndjson": ".ndjson", "sql": ".sql",
}


class ArtifactWriter:
    """Serialises masked/restored tables back into a downloadable artifact."""

    def write(
        self,
        tables: Mapping[str, pl.DataFrame],
        manifest: SourceManifest,
        fmt: Optional[str] = None,
        stem: Optional[str] = None,
        table_name_map: Optional[Mapping[str, str]] = None,
    ) -> Tuple[bytes, str, str]:
        kind = (fmt or manifest.source_kind or "csv").lower()
        if kind in ("postgres",):
            kind = "sql"
        if kind not in _EXTENSIONS:
            kind = "csv"

        base = stem or manifest.dataset_name or "dataset"
        name = f"{base}{_EXTENSIONS[kind]}"

        if kind == "csv":
            return self._csv(tables, manifest, name, "\t" if manifest.csv_separator == "\t" else manifest.csv_separator)
        if kind == "tsv":
            return self._csv(tables, manifest, name, "\t")
        if kind == "excel":
            return self._excel(tables, manifest, name, table_name_map)
        if kind == "parquet":
            return self._parquet(tables, manifest, name)
        if kind == "json":
            return self._json(tables, manifest, name, table_name_map)
        if kind == "ndjson":
            return self._ndjson(tables, manifest, name)
        return self._sql(tables, manifest, name, table_name_map)

    # ------------------------------------------------------------------ #
    @staticmethod
    def _ordered(
        tables: Mapping[str, pl.DataFrame], manifest: SourceManifest
    ) -> List[Tuple[str, pl.DataFrame]]:
        order = [t for t in manifest.table_order if t in tables]
        order += [t for t in tables if t not in order]
        return [(t, tables[t]) for t in order]

    # ------------------------------------------------------------------ #
    #  CSV
    # ------------------------------------------------------------------ #
    def _csv(
        self, tables: Mapping[str, pl.DataFrame], manifest: SourceManifest,
        name: str, sep: str,
    ) -> Tuple[bytes, str, str]:
        items = self._ordered(tables, manifest)
        if len(items) == 1:
            buf = io.BytesIO()
            items[0][1].write_csv(buf, separator=sep)
            return buf.getvalue(), name, MIME_TYPES["tsv" if sep == "\t" else "csv"]

        # Multi-table CSV export -> ZIP bundle (still a single artifact).
        import zipfile

        zbuf = io.BytesIO()
        with zipfile.ZipFile(zbuf, "w", zipfile.ZIP_DEFLATED) as zf:
            for tname, df in items:
                cbuf = io.BytesIO()
                df.write_csv(cbuf, separator=sep)
                zf.writestr(f"{tname}.csv", cbuf.getvalue())
        return zbuf.getvalue(), name.replace(".csv", ".zip").replace(".tsv", ".zip"), "application/zip"

    # ------------------------------------------------------------------ #
    #  Excel
    # ------------------------------------------------------------------ #
    def _excel(
        self, tables: Mapping[str, pl.DataFrame], manifest: SourceManifest,
        name: str, table_name_map: Optional[Mapping[str, str]],
    ) -> Tuple[bytes, str, str]:
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Font, PatternFill
        from openpyxl.utils import get_column_letter

        wb = Workbook()
        wb.remove(wb.active)

        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill("solid", fgColor="1F3A5F")
        align = Alignment(horizontal="left", vertical="center")

        for tname, df in self._ordered(tables, manifest):
            out_name = (table_name_map or {}).get(tname, tname)
            safe = self._safe_sheet_name(out_name)
            ws = wb.create_sheet(title=safe)

            ws.append(list(df.columns))
            for cell in ws[1]:
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = align

            for row in df.iter_rows():
                ws.append([self._excel_value(v) for v in row])

            # Re-apply captured formula strings for this sheet.
            for coord, formula in (manifest.excel_formulas.get(tname, {}) or {}).items():
                try:
                    ws[coord] = formula
                except Exception:
                    continue

            for i, col in enumerate(df.columns, start=1):
                width = max(
                    len(str(col)),
                    *(
                        [len(str(v)) for v in df.get_column(col).head(200).to_list()]
                        or [0]
                    ),
                )
                ws.column_dimensions[get_column_letter(i)].width = min(48, max(10, width + 2))
            ws.freeze_panes = "A2"

        if not wb.worksheets:
            wb.create_sheet(title="empty")

        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue(), name, MIME_TYPES["excel"]

    @staticmethod
    def _safe_sheet_name(name: str) -> str:
        bad = set(r"[]:*?/\\")
        cleaned = "".join("_" if c in bad else c for c in str(name))
        return (cleaned[:31] or "Sheet")

    @staticmethod
    def _excel_value(v: Any) -> Any:
        if v is None:
            return None
        if isinstance(v, (int, float, bool, str, datetime, date, time)):
            if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                return None
            return v
        if isinstance(v, Decimal):
            return float(v)
        return str(v)

    # ------------------------------------------------------------------ #
    #  Parquet
    # ------------------------------------------------------------------ #
    def _parquet(
        self, tables: Mapping[str, pl.DataFrame], manifest: SourceManifest, name: str
    ) -> Tuple[bytes, str, str]:
        items = self._ordered(tables, manifest)
        if len(items) == 1:
            buf = io.BytesIO()
            items[0][1].write_parquet(buf, compression="zstd")
            return buf.getvalue(), name, MIME_TYPES["parquet"]

        import zipfile

        zbuf = io.BytesIO()
        with zipfile.ZipFile(zbuf, "w", zipfile.ZIP_DEFLATED) as zf:
            for tname, df in items:
                pbuf = io.BytesIO()
                df.write_parquet(pbuf, compression="zstd")
                zf.writestr(f"{tname}.parquet", pbuf.getvalue())
        return zbuf.getvalue(), name.replace(".parquet", ".zip"), "application/zip"

    # ------------------------------------------------------------------ #
    #  JSON
    # ------------------------------------------------------------------ #
    def _json(
        self, tables: Mapping[str, pl.DataFrame], manifest: SourceManifest,
        name: str, table_name_map: Optional[Mapping[str, str]],
    ) -> Tuple[bytes, str, str]:
        items = self._ordered(tables, manifest)
        if manifest.json_root_kind == "table_map" or len(items) > 1:
            payload: Dict[str, Any] = {}
            for tname, df in items:
                out_name = (table_name_map or {}).get(tname, tname)
                payload[out_name] = df.to_dicts()
            blob = json.dumps(payload, indent=2, ensure_ascii=False, default=self._json_default)
        else:
            blob = json.dumps(
                items[0][1].to_dicts(), indent=2, ensure_ascii=False, default=self._json_default
            )
        return blob.encode("utf-8"), name, MIME_TYPES["json"]

    def _ndjson(
        self, tables: Mapping[str, pl.DataFrame], manifest: SourceManifest, name: str
    ) -> Tuple[bytes, str, str]:
        items = self._ordered(tables, manifest)
        lines = [
            json.dumps(rec, ensure_ascii=False, default=self._json_default)
            for _, df in items for rec in df.to_dicts()
        ]
        return ("\n".join(lines) + "\n").encode("utf-8"), name, MIME_TYPES["ndjson"]

    @staticmethod
    def _json_default(o: Any) -> Any:
        if isinstance(o, (datetime, date, time)):
            return o.isoformat()
        if isinstance(o, Decimal):
            return float(o)
        if isinstance(o, bytes):
            return o.decode("utf-8", errors="replace")
        return str(o)

    # ------------------------------------------------------------------ #
    #  SQL
    # ------------------------------------------------------------------ #
    def _sql(
        self, tables: Mapping[str, pl.DataFrame], manifest: SourceManifest,
        name: str, table_name_map: Optional[Mapping[str, str]],
    ) -> Tuple[bytes, str, str]:
        parts: List[str] = [
            "-- AetherMask (CipherShift) generated SQL artifact",
            "-- Air-gapped export. No external references.",
            "BEGIN;",
            "",
        ]
        for tname, df in self._ordered(tables, manifest):
            out_name = (table_name_map or {}).get(tname, tname)
            parts.append(self._create_table(out_name, df))
            parts.append("")
            if df.height:
                parts.append(self._inserts(out_name, df))
                parts.append("")
        parts.append("COMMIT;")
        return ("\n".join(parts)).encode("utf-8"), name, MIME_TYPES["sql"]

    @staticmethod
    def _pg_type(dtype: pl.DataType) -> str:
        if dtype in (pl.Int8, pl.Int16, pl.Int32, pl.UInt8, pl.UInt16):
            return "integer"
        if dtype in (pl.Int64, pl.UInt32, pl.UInt64):
            return "bigint"
        if dtype in (pl.Float32,):
            return "real"
        if dtype in (pl.Float64,):
            return "double precision"
        if dtype == pl.Boolean:
            return "boolean"
        if dtype == pl.Date:
            return "date"
        if isinstance(dtype, pl.Datetime) or dtype == pl.Datetime:
            return "timestamp"
        if dtype == pl.Time:
            return "time"
        return "text"

    @classmethod
    def _create_table(cls, table: str, df: pl.DataFrame) -> str:
        cols = ",\n  ".join(
            f'"{c}" {cls._pg_type(df.get_column(c).dtype)}' for c in df.columns
        )
        return f'CREATE TABLE IF NOT EXISTS "{table}" (\n  {cols}\n);'

    @classmethod
    def _inserts(cls, table: str, df: pl.DataFrame, chunk: int = 500) -> str:
        collist = ", ".join(f'"{c}"' for c in df.columns)
        out: List[str] = []
        rows = df.iter_rows()
        batch: List[str] = []
        for row in rows:
            batch.append("(" + ", ".join(cls._sql_literal(v) for v in row) + ")")
            if len(batch) >= chunk:
                out.append(
                    f'INSERT INTO "{table}" ({collist}) VALUES\n'
                    + ",\n".join(batch) + ";"
                )
                batch = []
        if batch:
            out.append(
                f'INSERT INTO "{table}" ({collist}) VALUES\n' + ",\n".join(batch) + ";"
            )
        return "\n".join(out)

    @staticmethod
    def _sql_literal(v: Any) -> str:
        if v is None:
            return "NULL"
        if isinstance(v, bool):
            return "TRUE" if v else "FALSE"
        if isinstance(v, (int,)):
            return str(v)
        if isinstance(v, float):
            if math.isnan(v) or math.isinf(v):
                return "NULL"
            return repr(v)
        if isinstance(v, Decimal):
            return str(v)
        if isinstance(v, (datetime, date, time)):
            return "'" + v.isoformat() + "'"
        s = str(v).replace("'", "''")
        return f"'{s}'"
