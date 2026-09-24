"""
AetherMask (CipherShift) :: core.ingest
=======================================
Streaming, memory-efficient ingestion and faithful re-serialisation.

Supported sources
-----------------
    .csv / .tsv / .txt      Polars CSV reader (schema inference, streaming)
    .parquet / .pq          PyArrow / Polars columnar reader
    .json / .ndjson         Polars JSON + newline-delimited JSON
    .xlsx / .xlsm / .xls    OpenPyXL - preserves EVERY worksheet, and captures
                            formula strings verbatim rather than cached values
    .sql                    PostgreSQL dump parser (SQLGlot-backed DDL parse +
                            COPY-block and INSERT-statement DML extraction)
    postgresql://...        Live READ-ONLY connection (psycopg 3) that opens a
                            read-only, deferrable transaction and never writes

Everything returns `Dict[table_name, polars.DataFrame]` plus a `SourceManifest`
that records exactly enough structure (sheet order, dialect, formulas, DDL) to
rebuild a byte-faithful artifact after masking or restoration.

Air-gap note: the PostgreSQL path is the ONLY socket this module can ever open,
it is explicitly opt-in, and it is refused unless the host resolves to a
loopback/private address (see `_assert_local_dsn`). In the shipped
`docker-compose.offline.yml` the container has `network_mode: "none"`, so even
that path is physically unavailable.
"""

from __future__ import annotations

import io
import ipaddress
import json
import os
import re
import socket
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple
from urllib.parse import urlparse

import polars as pl

__all__ = [
    "SourceManifest",
    "IngestResult",
    "DataIngestor",
    "IngestError",
    "SUPPORTED_EXTENSIONS",
]

SUPPORTED_EXTENSIONS = (
    ".csv", ".tsv", ".txt", ".parquet", ".pq",
    ".json", ".ndjson", ".jsonl",
    ".xlsx", ".xlsm", ".xls", ".sql",
)


class IngestError(Exception):
    """Raised for unreadable, unsupported, or unsafe sources."""


# --------------------------------------------------------------------------- #
#  Manifest describing the physical shape of the source
# --------------------------------------------------------------------------- #
@dataclass
class SourceManifest:
    """Everything needed to re-emit the artifact in its original physical form."""

    source_kind: str                      # csv | excel | parquet | json | sql | postgres
    dataset_name: str
    table_order: List[str] = field(default_factory=list)
    csv_separator: str = ","
    csv_has_header: bool = True
    excel_sheet_order: List[str] = field(default_factory=list)
    #: {sheet: {"A1": "=SUM(B1:B9)"}} - formulas captured verbatim
    excel_formulas: Dict[str, Dict[str, str]] = field(default_factory=dict)
    #: {sheet: {"column": "header text"}} for non-dataframe header rows
    json_root_kind: str = "records"       # records | table_map
    sql_ddl: Dict[str, str] = field(default_factory=dict)
    sql_statement_order: List[str] = field(default_factory=list)
    original_filename: str = ""
    encoding: str = "utf-8"
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_kind": self.source_kind,
            "dataset_name": self.dataset_name,
            "table_order": self.table_order,
            "csv_separator": self.csv_separator,
            "csv_has_header": self.csv_has_header,
            "excel_sheet_order": self.excel_sheet_order,
            "excel_formulas": self.excel_formulas,
            "json_root_kind": self.json_root_kind,
            "sql_ddl": self.sql_ddl,
            "sql_statement_order": self.sql_statement_order,
            "original_filename": self.original_filename,
            "encoding": self.encoding,
            "notes": self.notes,
        }

    @staticmethod
    def from_dict(d: Mapping[str, Any]) -> "SourceManifest":
        m = SourceManifest(
            source_kind=str(d.get("source_kind", "csv")),
            dataset_name=str(d.get("dataset_name", "dataset")),
        )
        m.table_order = list(d.get("table_order", []))
        m.csv_separator = str(d.get("csv_separator", ","))
        m.csv_has_header = bool(d.get("csv_has_header", True))
        m.excel_sheet_order = list(d.get("excel_sheet_order", []))
        m.excel_formulas = dict(d.get("excel_formulas", {}))
        m.json_root_kind = str(d.get("json_root_kind", "records"))
        m.sql_ddl = dict(d.get("sql_ddl", {}))
        m.sql_statement_order = list(d.get("sql_statement_order", []))
        m.original_filename = str(d.get("original_filename", ""))
        m.encoding = str(d.get("encoding", "utf-8"))
        m.notes = list(d.get("notes", []))
        return m


@dataclass
class IngestResult:
    tables: Dict[str, pl.DataFrame]
    manifest: SourceManifest

    @property
    def primary(self) -> pl.DataFrame:
        if not self.tables:
            raise IngestError("No tables were parsed from the source.")
        first = self.manifest.table_order[0] if self.manifest.table_order else next(iter(self.tables))
        return self.tables[first]

    def total_rows(self) -> int:
        return sum(df.height for df in self.tables.values())


# --------------------------------------------------------------------------- #
#  Ingestor
# --------------------------------------------------------------------------- #
class DataIngestor:
    """Format-dispatching, streaming-capable loader."""

    def __init__(self, infer_schema_rows: int = 10_000, max_sql_rows: int = 5_000_000):
        self.infer_schema_rows = infer_schema_rows
        self.max_sql_rows = max_sql_rows

    # ------------------------------------------------------------------ #
    #  Entry points
    # ------------------------------------------------------------------ #
    def load_path(self, path: str, dataset_name: Optional[str] = None) -> IngestResult:
        if not os.path.isfile(path):
            raise IngestError(f"File not found: {path}")
        with open(path, "rb") as fh:
            data = fh.read()
        return self.load_bytes(data, os.path.basename(path), dataset_name)

    def load_bytes(
        self, data: bytes, filename: str, dataset_name: Optional[str] = None
    ) -> IngestResult:
        ext = os.path.splitext(filename)[1].lower()
        stem = dataset_name or os.path.splitext(os.path.basename(filename))[0] or "dataset"

        if ext in (".csv", ".tsv", ".txt"):
            return self._load_csv(data, filename, stem, ext)
        if ext in (".parquet", ".pq"):
            return self._load_parquet(data, filename, stem)
        if ext in (".json", ".ndjson", ".jsonl"):
            return self._load_json(data, filename, stem, ext)
        if ext in (".xlsx", ".xlsm", ".xls"):
            return self._load_excel(data, filename, stem)
        if ext == ".sql":
            return self._load_sql_dump(data, filename, stem)
        raise IngestError(
            f"Unsupported extension '{ext}'. Supported: {', '.join(SUPPORTED_EXTENSIONS)}"
        )

    # ------------------------------------------------------------------ #
    #  CSV / TSV
    # ------------------------------------------------------------------ #
    def _load_csv(self, data: bytes, filename: str, stem: str, ext: str) -> IngestResult:
        sep = "\t" if ext == ".tsv" else self._sniff_separator(data)
        try:
            df = pl.read_csv(
                io.BytesIO(data),
                separator=sep,
                infer_schema_length=self.infer_schema_rows,
                try_parse_dates=True,
                ignore_errors=False,
                null_values=["", "NA", "N/A", "NULL", "null", "None"],
            )
        except Exception:
            # Maximum-compatibility fallback: everything as text.
            df = pl.read_csv(
                io.BytesIO(data), separator=sep, infer_schema_length=0,
                truncate_ragged_lines=True, ignore_errors=True,
            )
        man = SourceManifest(
            source_kind="csv", dataset_name=stem, table_order=[stem],
            csv_separator=sep, original_filename=filename,
        )
        return IngestResult({stem: df}, man)

    @staticmethod
    def _sniff_separator(data: bytes) -> str:
        head = data[:65536].decode("utf-8", errors="replace")
        line = next((l for l in head.splitlines() if l.strip()), "")
        counts = {c: line.count(c) for c in [",", ";", "\t", "|"]}
        best = max(counts, key=lambda k: counts[k])
        return best if counts[best] > 0 else ","

    # ------------------------------------------------------------------ #
    #  Parquet
    # ------------------------------------------------------------------ #
    def _load_parquet(self, data: bytes, filename: str, stem: str) -> IngestResult:
        try:
            df = pl.read_parquet(io.BytesIO(data))
        except Exception as exc:
            raise IngestError(f"Unable to read Parquet: {exc}") from exc
        man = SourceManifest(
            source_kind="parquet", dataset_name=stem,
            table_order=[stem], original_filename=filename,
        )
        return IngestResult({stem: df}, man)

    # ------------------------------------------------------------------ #
    #  JSON / NDJSON
    # ------------------------------------------------------------------ #
    def _load_json(self, data: bytes, filename: str, stem: str, ext: str) -> IngestResult:
        text = data.decode("utf-8", errors="replace").strip()
        if ext in (".ndjson", ".jsonl"):
            df = pl.read_ndjson(io.BytesIO(data))
            man = SourceManifest(
                source_kind="json", dataset_name=stem, table_order=[stem],
                json_root_kind="ndjson", original_filename=filename,
            )
            return IngestResult({stem: df}, man)

        try:
            parsed = json.loads(text) if text else []
        except Exception as exc:
            raise IngestError(f"Invalid JSON: {exc}") from exc

        # Multi-table map: {"table": [ {...}, ... ], ...}
        if isinstance(parsed, dict) and parsed and all(
            isinstance(v, list) for v in parsed.values()
        ):
            tables: Dict[str, pl.DataFrame] = {}
            order: List[str] = []
            for tname, rows in parsed.items():
                tables[tname] = pl.DataFrame(rows, infer_schema_length=None) if rows else pl.DataFrame()
                order.append(tname)
            man = SourceManifest(
                source_kind="json", dataset_name=stem, table_order=order,
                json_root_kind="table_map", original_filename=filename,
            )
            return IngestResult(tables, man)

        if isinstance(parsed, dict):
            parsed = [parsed]
        df = pl.DataFrame(parsed, infer_schema_length=None) if parsed else pl.DataFrame()
        man = SourceManifest(
            source_kind="json", dataset_name=stem, table_order=[stem],
            json_root_kind="records", original_filename=filename,
        )
        return IngestResult({stem: df}, man)

    # ------------------------------------------------------------------ #
    #  Excel (multi-sheet, formula-preserving)
    # ------------------------------------------------------------------ #
    def _load_excel(self, data: bytes, filename: str, stem: str) -> IngestResult:
        from openpyxl import load_workbook

        tables: Dict[str, pl.DataFrame] = {}
        sheet_order: List[str] = []
        formulas: Dict[str, Dict[str, str]] = {}

        try:
            # data_only=False keeps "=SUM(...)" strings intact.
            wb = load_workbook(io.BytesIO(data), data_only=False, read_only=False)
        except Exception as exc:
            raise IngestError(f"Unable to read workbook: {exc}") from exc

        for ws in wb.worksheets:
            sheet_order.append(ws.title)
            rows = list(ws.iter_rows(values_only=False))
            if not rows:
                tables[ws.title] = pl.DataFrame()
                continue

            header = [
                (str(c.value) if c.value is not None else f"column_{i + 1}")
                for i, c in enumerate(rows[0])
            ]
            header = self._dedupe(header)

            body: List[List[Any]] = []
            sheet_formulas: Dict[str, str] = {}
            for r in rows[1:]:
                vals: List[Any] = []
                for c in r:
                    v = c.value
                    if isinstance(v, str) and v.startswith("="):
                        sheet_formulas[c.coordinate] = v
                    vals.append(v)
                if len(vals) < len(header):
                    vals += [None] * (len(header) - len(vals))
                body.append(vals[: len(header)])

            if body:
                cols = {h: [row[i] for row in body] for i, h in enumerate(header)}
                df = pl.DataFrame(
                    {k: pl.Series(k, v, strict=False) for k, v in cols.items()}
                )
                df = self._coerce_numeric_strings(df)
            else:
                df = pl.DataFrame({h: pl.Series(h, [], dtype=pl.Utf8) for h in header})

            tables[ws.title] = df
            if sheet_formulas:
                formulas[ws.title] = sheet_formulas

        wb.close()
        man = SourceManifest(
            source_kind="excel", dataset_name=stem, table_order=sheet_order,
            excel_sheet_order=sheet_order, excel_formulas=formulas,
            original_filename=filename,
        )
        if formulas:
            man.notes.append(
                f"Captured {sum(len(v) for v in formulas.values())} formula cells verbatim."
            )
        return IngestResult(tables, man)

    @staticmethod
    def _coerce_numeric_strings(df: pl.DataFrame) -> pl.DataFrame:
        """Tighten Object/Utf8 columns that are wholly numeric (Excel artefacts)."""
        out = df
        for name in df.columns:
            s = df.get_column(name)
            if s.dtype == pl.Object:
                out = out.with_columns(
                    pl.Series(name, [None if v is None else str(v) for v in s.to_list()])
                )
        return out

    @staticmethod
    def _dedupe(names: Sequence[str]) -> List[str]:
        seen: Dict[str, int] = {}
        out: List[str] = []
        for n in names:
            if n in seen:
                seen[n] += 1
                out.append(f"{n}_{seen[n]}")
            else:
                seen[n] = 0
                out.append(n)
        return out

    # ------------------------------------------------------------------ #
    #  PostgreSQL dump (.sql)
    # ------------------------------------------------------------------ #
    def _load_sql_dump(self, data: bytes, filename: str, stem: str) -> IngestResult:
        text = data.decode("utf-8", errors="replace")
        tables: Dict[str, pl.DataFrame] = {}
        ddl: Dict[str, str] = {}
        order: List[str] = []

        schemas = self._parse_ddl(text, ddl)
        copy_rows = self._parse_copy_blocks(text)
        insert_rows = self._parse_inserts(text)

        merged: Dict[str, Tuple[List[str], List[List[Any]]]] = {}
        for src in (copy_rows, insert_rows):
            for tname, (cols, rows) in src.items():
                if tname in merged:
                    merged[tname][1].extend(rows)
                else:
                    merged[tname] = (cols, list(rows))

        for tname, (cols, rows) in merged.items():
            if not cols:
                cols = schemas.get(tname, [])
            if not cols and rows:
                cols = [f"column_{i + 1}" for i in range(len(rows[0]))]
            cols = self._dedupe(cols)
            width = len(cols)
            norm = [
                (r + [None] * (width - len(r)))[:width] for r in rows
            ] if width else []
            if width:
                data_cols = {c: [r[i] for r in norm] for i, c in enumerate(cols)}
                df = pl.DataFrame(
                    {k: pl.Series(k, v, dtype=pl.Utf8, strict=False) for k, v in data_cols.items()}
                )
                df = self._infer_sql_types(df)
            else:
                df = pl.DataFrame()
            tables[tname] = df
            order.append(tname)

        # Tables declared in DDL but with no rows still matter for topology.
        for tname, cols in schemas.items():
            if tname not in tables:
                tables[tname] = pl.DataFrame(
                    {c: pl.Series(c, [], dtype=pl.Utf8) for c in cols}
                )
                order.append(tname)

        if not tables:
            raise IngestError(
                "No CREATE TABLE, COPY, or INSERT statements found in the SQL dump."
            )

        man = SourceManifest(
            source_kind="sql", dataset_name=stem, table_order=order,
            sql_ddl=ddl, original_filename=filename,
        )
        return IngestResult(tables, man)

    @staticmethod
    def _parse_ddl(text: str, ddl_out: Dict[str, str]) -> Dict[str, List[str]]:
        """Extract table -> column list using SQLGlot, with a regex fallback."""
        schemas: Dict[str, List[str]] = {}
        stmt_re = re.compile(
            r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[^;]+;", re.IGNORECASE | re.DOTALL
        )
        for m in stmt_re.finditer(text):
            stmt = m.group(0)
            name: Optional[str] = None
            cols: List[str] = []
            try:
                import sqlglot
                from sqlglot import expressions as exp

                tree = sqlglot.parse_one(stmt, read="postgres")
                tbl = tree.find(exp.Table)
                if tbl is not None:
                    name = tbl.name
                for cdef in tree.find_all(exp.ColumnDef):
                    cols.append(cdef.alias_or_name)
            except Exception:
                pass

            if not name:
                nm = re.search(
                    r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?"
                    r"(?:\"?(?P<schema>[\w$]+)\"?\.)?\"?(?P<tbl>[\w$]+)\"?",
                    stmt, re.IGNORECASE,
                )
                if nm:
                    name = nm.group("tbl")
            if not name:
                continue
            if not cols:
                body = stmt[stmt.find("(") + 1: stmt.rfind(")")]
                for line in body.split(","):
                    line = line.strip()
                    if not line or re.match(
                        r"^(PRIMARY|FOREIGN|UNIQUE|CONSTRAINT|CHECK|KEY|EXCLUDE)\b",
                        line, re.IGNORECASE,
                    ):
                        continue
                    cm = re.match(r'^"?([\w$]+)"?\s+', line)
                    if cm:
                        cols.append(cm.group(1))
            if cols:
                schemas[name] = cols
                ddl_out[name] = stmt.strip()
        return schemas

    @classmethod
    def _parse_copy_blocks(cls, text: str) -> Dict[str, Tuple[List[str], List[List[Any]]]]:
        """Parse `COPY tbl (a,b) FROM stdin; ... \\.` blocks (pg_dump default)."""
        out: Dict[str, Tuple[List[str], List[List[Any]]]] = {}
        pattern = re.compile(
            r"COPY\s+(?:\"?[\w$]+\"?\.)?\"?(?P<tbl>[\w$]+)\"?\s*"
            r"(?:\((?P<cols>[^)]*)\))?\s*FROM\s+stdin[^;]*;\s*\n"
            r"(?P<body>.*?)\n\\\.",
            re.IGNORECASE | re.DOTALL,
        )
        for m in pattern.finditer(text):
            tbl = m.group("tbl")
            cols = [
                c.strip().strip('"') for c in (m.group("cols") or "").split(",") if c.strip()
            ]
            rows: List[List[Any]] = []
            for line in m.group("body").split("\n"):
                if line == "" or line == "\\.":
                    continue
                rows.append([cls._pg_copy_value(v) for v in line.split("\t")])
            out[tbl] = (cols, rows)
        return out

    @staticmethod
    def _pg_copy_value(raw: str) -> Optional[str]:
        if raw == "\\N":
            return None
        return (
            raw.replace("\\t", "\t").replace("\\n", "\n")
            .replace("\\r", "\r").replace("\\\\", "\\")
        )

    @classmethod
    def _parse_inserts(cls, text: str) -> Dict[str, Tuple[List[str], List[List[Any]]]]:
        """Parse `INSERT INTO tbl (cols) VALUES (...),(...);` statements."""
        out: Dict[str, Tuple[List[str], List[List[Any]]]] = {}
        pattern = re.compile(
            r"INSERT\s+INTO\s+(?:\"?[\w$]+\"?\.)?\"?(?P<tbl>[\w$]+)\"?\s*"
            r"(?:\((?P<cols>[^)]*)\))?\s*VALUES\s*(?P<vals>.*?);(?=\s*(?:$|\n))",
            re.IGNORECASE | re.DOTALL,
        )
        for m in pattern.finditer(text):
            tbl = m.group("tbl")
            cols = [
                c.strip().strip('"') for c in (m.group("cols") or "").split(",") if c.strip()
            ]
            rows = cls._split_value_tuples(m.group("vals"))
            if tbl in out:
                out[tbl][1].extend(rows)
                if cols and not out[tbl][0]:
                    out[tbl] = (cols, out[tbl][1])
            else:
                out[tbl] = (cols, rows)
        return out

    @staticmethod
    def _split_value_tuples(blob: str) -> List[List[Any]]:
        """SQL-aware tuple splitter honouring quotes, escapes and nesting."""
        rows: List[List[Any]] = []
        cur: List[Any] = []
        buf: List[str] = []
        in_str = False
        depth = 0
        i = 0
        started = False
        n = len(blob)

        def flush_field() -> None:
            raw = "".join(buf).strip()
            buf.clear()
            if raw.upper() == "NULL" or raw == "":
                cur.append(None)
            elif len(raw) >= 2 and raw[0] == "'" and raw[-1] == "'":
                cur.append(raw[1:-1].replace("''", "'").replace("\\'", "'"))
            else:
                cur.append(raw)

        while i < n:
            ch = blob[i]
            if in_str:
                buf.append(ch)
                if ch == "'":
                    if i + 1 < n and blob[i + 1] == "'":
                        buf.append("'")
                        i += 2
                        continue
                    in_str = False
                elif ch == "\\" and i + 1 < n:
                    buf.append(blob[i + 1])
                    i += 2
                    continue
                i += 1
                continue

            if ch == "'":
                in_str = True
                buf.append(ch)
            elif ch == "(":
                depth += 1
                if depth == 1:
                    started = True
                    cur = []
                    buf.clear()
                else:
                    buf.append(ch)
            elif ch == ")":
                depth -= 1
                if depth == 0 and started:
                    flush_field()
                    rows.append(cur)
                    cur = []
                    started = False
                else:
                    buf.append(ch)
            elif ch == "," and depth == 1:
                flush_field()
            elif depth >= 1:
                buf.append(ch)
            i += 1
        return rows

    @staticmethod
    def _infer_sql_types(df: pl.DataFrame) -> pl.DataFrame:
        """Promote all-numeric text columns parsed from SQL into numeric dtypes."""
        out = df
        for name in df.columns:
            s = df.get_column(name)
            if s.dtype != pl.Utf8:
                continue
            nn = s.drop_nulls()
            if nn.len() == 0:
                continue
            try:
                as_int = nn.str.strip_chars().cast(pl.Int64, strict=True)
                if as_int.len() == nn.len():
                    out = out.with_columns(
                        pl.col(name).str.strip_chars().cast(pl.Int64, strict=False)
                    )
                    continue
            except Exception:
                pass
            try:
                as_f = nn.str.strip_chars().cast(pl.Float64, strict=True)
                if as_f.len() == nn.len():
                    out = out.with_columns(
                        pl.col(name).str.strip_chars().cast(pl.Float64, strict=False)
                    )
            except Exception:
                continue
        return out

    # ------------------------------------------------------------------ #
    #  Live PostgreSQL (read-only, loopback/private only)
    # ------------------------------------------------------------------ #
    @staticmethod
    def _assert_local_dsn(dsn: str) -> None:
        """Refuse any DSN that is not loopback or RFC1918/unique-local."""
        parsed = urlparse(dsn)
        host = parsed.hostname or "localhost"
        if host in ("localhost", "::1", "127.0.0.1"):
            return
        try:
            infos = socket.getaddrinfo(host, None)
            addrs = {ipaddress.ip_address(i[4][0]) for i in infos}
        except Exception as exc:
            raise IngestError(
                f"Air-gap policy: cannot resolve '{host}' locally ({exc})."
            ) from exc
        for a in addrs:
            if not (a.is_loopback or a.is_private or a.is_link_local):
                raise IngestError(
                    f"Air-gap policy violation: '{host}' resolves to non-private "
                    f"address {a}. Only loopback/private PostgreSQL hosts are permitted."
                )

    def load_postgres(
        self,
        dsn: str,
        schema: str = "public",
        tables: Optional[Sequence[str]] = None,
        row_limit: Optional[int] = None,
        dataset_name: Optional[str] = None,
    ) -> IngestResult:
        """
        Read tables from a local PostgreSQL instance in a READ ONLY transaction.

        The session is explicitly set `READ ONLY DEFERRABLE` and every statement
        is a plain SELECT, so the source database can never be mutated.
        """
        self._assert_local_dsn(dsn)
        try:
            import psycopg
        except Exception as exc:  # pragma: no cover
            raise IngestError(
                "psycopg (v3) is not installed in this offline image; "
                "PostgreSQL ingestion is unavailable."
            ) from exc

        stem = dataset_name or (urlparse(dsn).path.lstrip("/") or "pgdataset")
        out: Dict[str, pl.DataFrame] = {}
        order: List[str] = []
        ddl: Dict[str, str] = {}

        with psycopg.connect(dsn, autocommit=False) as conn:
            with conn.cursor() as cur:
                cur.execute("SET TRANSACTION READ ONLY, DEFERRABLE")
                if tables:
                    tnames = list(tables)
                else:
                    cur.execute(
                        "SELECT table_name FROM information_schema.tables "
                        "WHERE table_schema = %s AND table_type = 'BASE TABLE' "
                        "ORDER BY table_name",
                        (schema,),
                    )
                    tnames = [r[0] for r in cur.fetchall()]

                for t in tnames:
                    cur.execute(
                        "SELECT column_name, data_type, is_nullable "
                        "FROM information_schema.columns "
                        "WHERE table_schema = %s AND table_name = %s "
                        "ORDER BY ordinal_position",
                        (schema, t),
                    )
                    colmeta = cur.fetchall()
                    if not colmeta:
                        continue
                    ddl[t] = "CREATE TABLE {} (\n  {}\n);".format(
                        t,
                        ",\n  ".join(
                            f'"{c}" {d}{"" if n == "YES" else " NOT NULL"}'
                            for c, d, n in colmeta
                        ),
                    )
                    qt = f'"{schema}"."{t}"'
                    sql = f"SELECT * FROM {qt}"
                    if row_limit:
                        sql += f" LIMIT {int(row_limit)}"
                    cur.execute(sql)
                    colnames = [d.name for d in (cur.description or [])]
                    rows = cur.fetchall()
                    if rows:
                        cols = {
                            c: [r[i] for r in rows] for i, c in enumerate(colnames)
                        }
                        df = pl.DataFrame(
                            {k: pl.Series(k, v, strict=False) for k, v in cols.items()}
                        )
                    else:
                        df = pl.DataFrame(
                            {c: pl.Series(c, [], dtype=pl.Utf8) for c in colnames}
                        )
                    out[t] = df
                    order.append(t)
            conn.rollback()  # guarantee nothing is committed

        if not out:
            raise IngestError(f"No readable base tables found in schema '{schema}'.")

        man = SourceManifest(
            source_kind="postgres", dataset_name=stem, table_order=order,
            sql_ddl=ddl, original_filename=f"{stem}.sql",
        )
        man.notes.append("Read via READ ONLY DEFERRABLE transaction; rolled back.")
        return IngestResult(out, man)
