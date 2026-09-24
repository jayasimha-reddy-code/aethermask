/**
 * AetherMask (CipherShift) :: API contract types
 *
 * These mirror the JSON emitted by `api/server.py` exactly. They are the
 * single source of truth for the Data Studio; no component re-declares a
 * server shape locally.
 */

export interface FramePreview {
  columns: string[];
  dtypes: string[];
  rows: (string | number | boolean | null)[][];
  total_rows: number;
  total_columns: number;
}

export interface ChartPoint {
  name: string;
  value: number;
  count: number;
}

export interface ChartBlock {
  category_column: string;
  measure_column: string;
  masked_category_column: string;
  masked_measure_column: string;
  original_series: ChartPoint[];
  sanitized_series: ChartPoint[];
}

export interface DomainProfileInfo {
  key: string;
  title: string;
  source_domain: string;
  cover_domain: string;
  description: string;
  token_rules: string;
  /** Surrogate pool size per semantic class (v2 lexicon expansion). */
  pool_sizes?: Record<string, number>;
  /** Total surrogates available across all classes, as a string. */
  pool_capacity?: string;
}

export interface ColumnFinding {
  rule_id: string;
  category: string;
  severity: number;
  matched_in: string[];
  explanation: string;
  evidence: string[];
}

export interface ColumnProfileInfo {
  name: string;
  dtype: string;
  semantic_role: string;
  distinct_count: number;
  null_count: number;
  row_count: number;
  cardinality_ratio: number;
  is_unique: boolean;
  max_severity: number;
  findings: ColumnFinding[];
  top_categories: { value: string | null; count: number; rank?: number }[];
  numeric_stats?: Record<string, number> | null;
}

export interface TableProfileInfo {
  name: string;
  row_count: number;
  columns: ColumnProfileInfo[];
  primary_key_candidates: string[];
  schema_fingerprint: string;
}

export interface ProfileResponse {
  dataset_name: string;
  risk_grade: string;
  risk_score: number;
  recommended_profile: string;
  finding_summary: Record<string, number>;
  dataset_fingerprint: string;
  total_rows: number;
  table_count: number;
  tables: TableProfileInfo[];
  foreign_keys: Record<string, unknown>[];
  source?: Record<string, unknown>;
}

export interface FidelityReportInfo {
  passed: boolean;
  total_checks: number;
  passed_checks: number;
  failed_checks: number;
  failures: string[];
}

export interface ArtifactInfo {
  filename: string;
  mime_type: string;
  size_bytes: number;
  sha256: string;
  base64: string;
}

export interface ObfuscateResponse {
  status: string;
  dataset_name: string;
  domain_profile: string;
  profile_title: string;
  schema_fingerprint: string;
  artifact: ArtifactInfo;
  ciphermap: { filename: string; manifest: Record<string, unknown> };
  fidelity: FidelityReportInfo;
  statistics: {
    tables: number;
    total_rows: number;
    columns_renamed: number;
    values_substituted: number;
    table_name_map: Record<string, string>;
  };
  engine: Record<string, unknown>;
  preview?: {
    table: string;
    masked_table: string;
    original: FramePreview;
    sanitized: FramePreview;
    column_map: Record<string, string>;
    column_strategies: Record<string, string>;
    chart?: ChartBlock;
  };
}

export interface RestoreResponse {
  status: string;
  artifact: ArtifactInfo;
  statistics: {
    tables: number;
    total_rows: number;
    columns_restored: number;
    values_restored: number;
    table_name_map: Record<string, string>;
  };
  vault: Record<string, unknown>;
  preview?: { table: string; restored: FramePreview };
}

export interface AttestationResponse {
  product: string;
  version: string;
  airgap: {
    egress_blocking: boolean;
    blocked_attempts: number;
    events: unknown[];
    external_apis: string;
    cdn_assets: string;
    telemetry: string;
    model_downloads: string;
  };
  cryptography: Record<string, unknown>;
  kdf_policy: Record<string, unknown>;
  nlp: Record<string, unknown>;
  engine: Record<string, unknown>;
  lexicon?: {
    profiles: number;
    total_unique_surrogates: number;
    total_token_shift_rules: number;
    sensitivity_rules: number;
    ner_patterns: number;
    surrogate_pools_per_profile?: Record<string, Record<string, number>>;
  };
  supported_formats: string[];
}

export type Stage =
  | 'ingest'
  | 'profile'
  | 'transform'
  | 'export'
  | 'restore'
  | 'audit';

export type NumericMode = 'identity' | 'affine';
