"""
AetherMask (CipherShift) :: core.profiler
=========================================
Relational introspection + offline sensitivity profiling.

Produces, for every table/column:
  * physical dtype, null count / nullability, distinct count, cardinality ratio
  * inferred semantic role (identifier / categorical / measure / temporal /
    free-text / geospatial / boolean)
  * primary-key and foreign-key candidates (uniqueness + inclusion-dependency
    analysis executed locally on Polars frames)
  * sensitivity findings from the deterministic regex/gazetteer ruleset, with
    severity scoring, sampled evidence, and an aggregate risk grade

Every scan runs on local CPU over Polars frames. Column values are sampled for
evidence but the profiler NEVER retains full column data on the returned object,
which satisfies the "analyses schema without retaining data" contract of the
`/api/v1/profile` endpoint.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
from typing import Any

import polars as pl

from .ontology import SENSITIVITY_RULES

__all__ = [
    "ColumnProfile",
    "DatasetProfile",
    "SemanticRole",
    "SensitivityProfiler",
    "TableProfile",
]


# --------------------------------------------------------------------------- #
#  Compiled ruleset (module-level, compiled once)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class _CompiledRule:
    id: str
    severity: int
    target: str
    category: str
    explain: str
    regex: re.Pattern[str]


_RULES: list[_CompiledRule] = [
    _CompiledRule(
        id=str(r["id"]),
        severity=int(r["severity"]),  # type: ignore[arg-type]
        target=str(r["target"]),
        category=str(r["category"]),
        explain=str(r["explain"]),
        regex=re.compile(str(r["pattern"]), re.IGNORECASE),
    )
    for r in SENSITIVITY_RULES
]


class SemanticRole:
    IDENTIFIER = "identifier"
    CATEGORICAL = "categorical"
    MEASURE = "measure"
    TEMPORAL = "temporal"
    FREE_TEXT = "free_text"
    GEOSPATIAL = "geospatial"
    BOOLEAN = "boolean"
    CONSTANT = "constant"
    EMPTY = "empty"


_GEO_NAME = re.compile(
    r"\b(lat(itude)?|lon(g|gitude)?|coord(inate)?s?|geohash|mgrs|utm|easting|northing|"
    r"elev(ation)?|alt(itude)?)\b",
    re.IGNORECASE,
)
_ID_NAME = re.compile(r"(^|_)(id|uuid|guid|key|code|ref|no|num|number|serial)($|_)", re.IGNORECASE)

#: Separators that must be treated as word boundaries for header matching.
#: NOTE: Python's `\b` does NOT fire next to "_" (underscore is a word
#: character), so "target_latitude" would never match r"\blatitude\b". Every
#: header is therefore normalised to space-delimited tokens before matching.
_HEADER_SEPS = re.compile(r"[_\-./\\:|]+")


def _tokenized(name: str) -> str:
    """Space-delimit a header so that `\\b`-anchored rules match its tokens."""
    return _HEADER_SEPS.sub(" ", str(name))


# --------------------------------------------------------------------------- #
#  Dataclasses
# --------------------------------------------------------------------------- #
@dataclass
class ColumnProfile:
    name: str
    dtype: str
    position: int
    row_count: int
    null_count: int
    distinct_count: int
    cardinality_ratio: float
    is_unique: bool
    is_nullable: bool
    semantic_role: str
    sample_values: list[str] = field(default_factory=list)
    findings: list[dict[str, Any]] = field(default_factory=list)
    max_severity: int = 0
    numeric_stats: dict[str, float] | None = None
    top_categories: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TableProfile:
    name: str
    row_count: int
    columns: list[ColumnProfile]
    primary_key_candidates: list[str] = field(default_factory=list)
    composite_key_candidates: list[list[str]] = field(default_factory=list)
    schema_fingerprint: str = ""

    def column(self, name: str) -> ColumnProfile | None:
        for c in self.columns:
            if c.name == name:
                return c
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "row_count": self.row_count,
            "columns": [c.to_dict() for c in self.columns],
            "primary_key_candidates": self.primary_key_candidates,
            "composite_key_candidates": self.composite_key_candidates,
            "schema_fingerprint": self.schema_fingerprint,
        }


@dataclass
class DatasetProfile:
    dataset_name: str
    tables: list[TableProfile]
    foreign_keys: list[dict[str, Any]] = field(default_factory=list)
    dataset_fingerprint: str = ""
    risk_grade: str = "LOW"
    risk_score: float = 0.0
    finding_summary: dict[str, int] = field(default_factory=dict)
    recommended_profile: str = "generic_pii_redaction"

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_name": self.dataset_name,
            "tables": [t.to_dict() for t in self.tables],
            "foreign_keys": self.foreign_keys,
            "dataset_fingerprint": self.dataset_fingerprint,
            "risk_grade": self.risk_grade,
            "risk_score": self.risk_score,
            "finding_summary": self.finding_summary,
            "recommended_profile": self.recommended_profile,
        }


# --------------------------------------------------------------------------- #
#  Profiler
# --------------------------------------------------------------------------- #
class SensitivityProfiler:
    """Offline schema introspection + sensitivity scanning."""

    def __init__(
        self,
        value_sample_size: int = 500,
        max_evidence: int = 3,
        max_top_categories: int = 12,
        redact_values: bool = False,
    ) -> None:
        """
        Parameters
        ----------
        redact_values : when True the profile carries NO raw cell values.
            Sample values and category labels are replaced with redacted
            fragments while every statistic (counts, cardinality, frequency
            shape) is retained verbatim. The `/api/v1/profile` endpoint uses
            this mode so a schema analysis can be shared low-side without
            disclosing the confidential contents it describes.
        """
        self.value_sample_size = value_sample_size
        self.max_evidence = max_evidence
        self.max_top_categories = max_top_categories
        self.redact_values = redact_values

    # ------------------------------------------------------------------ #
    #  Column-level
    # ------------------------------------------------------------------ #
    def profile_column(self, df: pl.DataFrame, name: str, position: int) -> ColumnProfile:
        s = df.get_column(name)
        n = df.height
        nulls = int(s.null_count())
        try:
            distinct = int(s.n_unique())
        except Exception:
            distinct = int(s.cast(pl.Utf8, strict=False).n_unique())
        non_null = n - nulls
        ratio = (distinct / non_null) if non_null else 0.0
        dtype = str(s.dtype)

        # --- sampled string view (evidence only, never retained wholesale) --
        sample_n = min(self.value_sample_size, n)
        try:
            sample_series = s.head(sample_n).cast(pl.Utf8, strict=False).drop_nulls()
            sample_vals = [str(v) for v in sample_series.to_list()]
        except Exception:
            sample_vals = []

        role = self._infer_role(name, s, dtype, distinct, non_null, ratio, sample_vals)

        numeric_stats: dict[str, float] | None = None
        if s.dtype.is_numeric() and non_null:
            try:
                numeric_stats = {
                    "min": float(s.min()),           # type: ignore[arg-type]
                    "max": float(s.max()),           # type: ignore[arg-type]
                    "mean": float(s.mean()),         # type: ignore[arg-type]
                    "sum": float(s.sum()),           # type: ignore[arg-type]
                    "std": float(s.std()) if non_null > 1 and s.std() is not None else 0.0,
                }
            except Exception:
                numeric_stats = None

        top_categories: list[dict[str, Any]] = []
        if role in (SemanticRole.CATEGORICAL, SemanticRole.BOOLEAN) and non_null:
            try:
                vc = (
                    df.select(pl.col(name).cast(pl.Utf8, strict=False))
                    .to_series()
                    .value_counts(sort=True)
                    .head(self.max_top_categories)
                )
                cnt_col = vc.columns[-1]
                for rank, row in enumerate(vc.iter_rows(named=True), start=1):
                    label = row[name]
                    top_categories.append(
                        {
                            "value": (
                                self._redact_evidence(str(label))
                                if (self.redact_values and label is not None)
                                else label
                            ),
                            "count": int(row[cnt_col]),
                            "rank": rank,
                        }
                    )
            except Exception:
                top_categories = []

        findings = self._scan(name, sample_vals)
        max_sev = max((int(f["severity"]) for f in findings), default=0)

        return ColumnProfile(
            name=name,
            dtype=dtype,
            position=position,
            row_count=n,
            null_count=nulls,
            distinct_count=distinct,
            cardinality_ratio=round(ratio, 6),
            is_unique=(non_null > 0 and distinct == non_null),
            is_nullable=(nulls > 0),
            semantic_role=role,
            sample_values=(
                [self._redact_evidence(v) for v in sample_vals[:5]]
                if self.redact_values else sample_vals[:5]
            ),
            findings=findings,
            max_severity=max_sev,
            numeric_stats=numeric_stats,
            top_categories=top_categories,
        )

    @staticmethod
    def _infer_role(
        name: str, s: pl.Series, dtype: str, distinct: int,
        non_null: int, ratio: float, samples: Sequence[str],
    ) -> str:
        if non_null == 0:
            return SemanticRole.EMPTY
        if distinct == 1:
            return SemanticRole.CONSTANT
        if s.dtype == pl.Boolean:
            return SemanticRole.BOOLEAN
        if s.dtype in (pl.Date, pl.Datetime, pl.Time, pl.Duration):
            return SemanticRole.TEMPORAL
        tname = _tokenized(name)
        if _GEO_NAME.search(tname):
            return SemanticRole.GEOSPATIAL
        if s.dtype.is_numeric():
            # Integer-typed high-cardinality columns named like keys are IDs.
            if _ID_NAME.search(name) and ratio > 0.9:
                return SemanticRole.IDENTIFIER
            if distinct <= 2:
                return SemanticRole.BOOLEAN
            return SemanticRole.MEASURE
        # String-ish
        avg_len = (sum(len(v) for v in samples) / len(samples)) if samples else 0
        word_avg = (
            sum(len(v.split()) for v in samples) / len(samples) if samples else 0
        )
        if ratio > 0.92 and (_ID_NAME.search(name) or avg_len <= 40):
            return SemanticRole.IDENTIFIER
        if word_avg >= 5 or avg_len >= 60:
            return SemanticRole.FREE_TEXT
        return SemanticRole.CATEGORICAL

    def _scan(self, name: str, samples: Sequence[str]) -> list[dict[str, Any]]:
        findings: list[dict[str, Any]] = []
        seen: set[str] = set()

        for rule in _RULES:
            hits: list[str] = []
            where: list[str] = []

            if rule.target in ("name", "both") and (
                rule.regex.search(name) or rule.regex.search(_tokenized(name))
            ):
                where.append("column_name")
                hits.append(name)

            if rule.target in ("value", "both"):
                vhits = 0
                for v in samples:
                    m = rule.regex.search(v)
                    if m:
                        vhits += 1
                        if len(hits) < self.max_evidence:
                            hits.append(self._redact_evidence(m.group(0)))
                if vhits:
                    where.append("values")

            if where and rule.id not in seen:
                seen.add(rule.id)
                findings.append(
                    {
                        "rule_id": rule.id,
                        "category": rule.category,
                        "severity": rule.severity,
                        "matched_in": where,
                        "explanation": rule.explain,
                        "evidence": hits[: self.max_evidence],
                    }
                )
        findings.sort(key=lambda f: (-int(f["severity"]), str(f["rule_id"])))
        return findings

    @staticmethod
    def _redact_evidence(text: str) -> str:
        """Partially mask evidence so the profile report itself is low-side safe."""
        t = str(text)
        if len(t) <= 4:
            return t[0] + "*" * (len(t) - 1) if t else ""
        keep = max(2, len(t) // 4)
        return f"{t[:keep]}{'*' * min(8, len(t) - keep * 2)}{t[-keep:]}"

    # ------------------------------------------------------------------ #
    #  Table-level
    # ------------------------------------------------------------------ #
    def profile_table(self, df: pl.DataFrame, name: str = "table") -> TableProfile:
        from .security import CipherVault

        cols = [
            self.profile_column(df, c, i) for i, c in enumerate(df.columns)
        ]
        pk = [c.name for c in cols if c.is_unique and not c.is_nullable and df.height > 0]
        composite = self._composite_keys(df, cols) if not pk else []
        fp = CipherVault.schema_fingerprint(
            [(c.name, c.dtype) for c in cols], table=name
        )
        return TableProfile(
            name=name,
            row_count=df.height,
            columns=cols,
            primary_key_candidates=pk,
            composite_key_candidates=composite,
            schema_fingerprint=fp,
        )

    @staticmethod
    def _composite_keys(
        df: pl.DataFrame, cols: Sequence[ColumnProfile], max_pairs: int = 40
    ) -> list[list[str]]:
        """Search 2-column composite keys among medium-cardinality columns."""
        if df.height == 0:
            return []
        cands = [
            c.name for c in cols
            if c.semantic_role in (
                SemanticRole.IDENTIFIER, SemanticRole.CATEGORICAL,
                SemanticRole.TEMPORAL, SemanticRole.MEASURE,
            )
            and c.distinct_count > 1 and not c.is_nullable
        ][:12]
        found: list[list[str]] = []
        tried = 0
        for i in range(len(cands)):
            for j in range(i + 1, len(cands)):
                if tried >= max_pairs or len(found) >= 3:
                    return found
                tried += 1
                pair = [cands[i], cands[j]]
                try:
                    if df.select(pair).n_unique() == df.height:
                        found.append(pair)
                except Exception:
                    continue
        return found

    # ------------------------------------------------------------------ #
    #  Dataset-level (relational topology)
    # ------------------------------------------------------------------ #
    def profile_dataset(
        self, tables: Mapping[str, pl.DataFrame], dataset_name: str = "dataset"
    ) -> DatasetProfile:
        from .security import CipherVault

        tprofiles = [self.profile_table(df, name) for name, df in tables.items()]
        fks = self._detect_foreign_keys(tables, tprofiles)

        summary: dict[str, int] = {}
        weighted = 0.0
        total_cols = 0
        for tp in tprofiles:
            for c in tp.columns:
                total_cols += 1
                weighted += c.max_severity
                for f in c.findings:
                    cat = str(f["category"])
                    summary[cat] = summary.get(cat, 0) + 1

        score = round((weighted / (total_cols * 5)) * 100, 2) if total_cols else 0.0
        if score >= 45:
            grade = "CRITICAL"
        elif score >= 28:
            grade = "HIGH"
        elif score >= 12:
            grade = "MODERATE"
        else:
            grade = "LOW"

        ds_fp = CipherVault.multi_table_fingerprint(
            {tp.name: [(c.name, c.dtype) for c in tp.columns] for tp in tprofiles}
        )

        return DatasetProfile(
            dataset_name=dataset_name,
            tables=tprofiles,
            foreign_keys=fks,
            dataset_fingerprint=ds_fp,
            risk_grade=grade,
            risk_score=score,
            finding_summary=summary,
            recommended_profile=self._recommend_profile(summary),
        )

    @staticmethod
    def _recommend_profile(summary: Mapping[str, int]) -> str:
        cyber = summary.get("cyber", 0)
        kinetic = summary.get("kinetic", 0)
        intel = summary.get("intelligence", 0)
        pii = summary.get("pii", 0)
        if cyber and cyber >= kinetic:
            return "cyberwar_to_smartgrid"
        if kinetic or intel or summary.get("orbat", 0) or summary.get("callsign", 0):
            return "defense_to_logistics"
        if pii:
            return "generic_pii_redaction"
        return "generic_pii_redaction"

    @staticmethod
    def _detect_foreign_keys(
        tables: Mapping[str, pl.DataFrame], profiles: Sequence[TableProfile]
    ) -> list[dict[str, Any]]:
        """
        Inclusion-dependency detection: child.col ⊆ parent.pk (>= 95% coverage).
        Runs entirely in-memory on local CPU via Polars set semantics.
        """
        by_name = {p.name: p for p in profiles}
        parents: list[tuple[str, str]] = []
        for p in profiles:
            for pk in p.primary_key_candidates:
                col = p.column(pk)
                if col and col.distinct_count > 1:
                    parents.append((p.name, pk))

        fks: list[dict[str, Any]] = []
        for child_name, child_df in tables.items():
            cp = by_name[child_name]
            for ccol in cp.columns:
                if ccol.semantic_role not in (
                    SemanticRole.IDENTIFIER, SemanticRole.CATEGORICAL
                ):
                    continue
                if ccol.distinct_count <= 1:
                    continue
                for parent_name, pk in parents:
                    if parent_name == child_name and pk == ccol.name:
                        continue
                    pcol = by_name[parent_name].column(pk)
                    if pcol is None or pcol.dtype != ccol.dtype:
                        continue
                    if ccol.is_unique and ccol.name == pk and parent_name == child_name:
                        continue
                    try:
                        child_vals = (
                            child_df.get_column(ccol.name)
                            .drop_nulls().unique().cast(pl.Utf8, strict=False)
                        )
                        if child_vals.len() == 0:
                            continue
                        parent_vals = set(
                            tables[parent_name]
                            .get_column(pk)
                            .drop_nulls().unique()
                            .cast(pl.Utf8, strict=False).to_list()
                        )
                        contained = sum(
                            1 for v in child_vals.to_list() if v in parent_vals
                        )
                        coverage = contained / child_vals.len()
                    except Exception:
                        continue
                    if coverage >= 0.95:
                        fks.append(
                            {
                                "child_table": child_name,
                                "child_column": ccol.name,
                                "parent_table": parent_name,
                                "parent_column": pk,
                                "coverage": round(coverage, 4),
                                "confidence": "high" if coverage == 1.0 else "probable",
                            }
                        )
                        break
        return fks
