/**
 * AetherMask (CipherShift) :: offline API client
 *
 * AIR-GAP CONTRACT
 * ----------------
 * Every request below targets a RELATIVE path under `/api/v1`. There is no
 * absolute origin, no configurable base URL, and no third-party endpoint
 * anywhere in this module. `assertRelative()` enforces that invariant at
 * runtime, so a future edit that accidentally introduces an external host
 * fails loudly instead of silently leaking data.
 */

import type {
  AttestationResponse,
  ChartBlock,
  DomainProfileInfo,
  FidelityReportInfo,
  FramePreview,
  NumericMode,
  ObfuscateResponse,
  ProfileResponse,
  RestoreResponse,
} from './types';

const API = '/api/v1';

/** Hard guard: refuse to issue any request that is not same-origin relative. */
export function assertRelative(path: string): string {
  if (/^[a-z][a-z0-9+.-]*:/i.test(path) || path.startsWith('//')) {
    throw new Error(
      `AetherMask air-gap violation: refusing non-relative request to "${path}"`,
    );
  }
  return path;
}

export class ApiError extends Error {
  readonly status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

/** Extract the most useful message the server offered. */
async function explain(res: Response): Promise<string> {
  let body = '';
  try {
    body = await res.text();
  } catch {
    /* body already consumed or unavailable */
  }
  if (body) {
    try {
      const parsed = JSON.parse(body) as { detail?: unknown };
      if (typeof parsed.detail === 'string') return parsed.detail;
      if (Array.isArray(parsed.detail) && parsed.detail.length > 0) {
        const first = parsed.detail[0] as { msg?: string };
        if (first?.msg) return first.msg;
      }
      if (parsed.detail) return JSON.stringify(parsed.detail);
    } catch {
      const clean = body.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();
      return clean.length > 200 ? `${clean.slice(0, 200)}...` : clean || `${res.status} ${res.statusText}`;
    }
  }
  return `${res.status} ${res.statusText}`;
}

const SAME_ORIGIN = ('same-origin' as const);

async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const res = await fetch(assertRelative(`${API}${path}`), {
    method: 'GET',
    credentials: SAME_ORIGIN,
    cache: 'no-store',
    signal,
  });
  if (!res.ok) throw new ApiError(await explain(res), res.status);
  return (await res.json()) as T;
}

async function postForm<T>(
  path: string,
  form: FormData,
  signal?: AbortSignal,
): Promise<T> {
  const res = await fetch(assertRelative(`${API}${path}`), {
    method: 'POST',
    body: form,
    credentials: SAME_ORIGIN,
    cache: 'no-store',
    signal,
  });
  if (!res.ok) throw new ApiError(await explain(res), res.status);
  return (await res.json()) as T;
}

/* -------------------------------------------------------------------------- */
/*  Endpoints                                                                  */
/* -------------------------------------------------------------------------- */

export function fetchProfiles(signal?: AbortSignal) {
  return getJson<{
    profiles: DomainProfileInfo[];
    count: number;
    lexicon?: { total_unique_surrogates: number };
  }>('/profiles', signal);
}

export function fetchAttestation(signal?: AbortSignal) {
  return getJson<AttestationResponse>('/attestation', signal);
}

export function fetchHealth(signal?: AbortSignal) {
  return getJson<Record<string, unknown>>('/health', signal);
}

export function profileDataset(
  file: File,
  datasetName?: string,
  signal?: AbortSignal,
) {
  const fd = new FormData();
  fd.append('file', file);
  if (datasetName) fd.append('dataset_name', datasetName);
  return postForm<ProfileResponse>('/profile', fd, signal);
}

export interface ObfuscateArgs {
  file: File;
  passphrase: string;
  domainProfile: string;
  numericMode: NumericMode;
  outputFormat?: string;
  seed?: string;
  includePreview?: boolean;
}

export function obfuscate(args: ObfuscateArgs, signal?: AbortSignal) {
  const fd = new FormData();
  fd.append('file', args.file);
  fd.append('passphrase', args.passphrase);
  fd.append('domain_profile', args.domainProfile);
  fd.append('numeric_mode', args.numericMode);
  fd.append('include_preview', String(args.includePreview ?? true));
  if (args.outputFormat) fd.append('output_format', args.outputFormat);
  if (args.seed) fd.append('seed', args.seed);
  return postForm<ObfuscateResponse>('/obfuscate', fd, signal);
}

export interface RestoreArgs {
  file: File;
  ciphermap: File;
  passphrase: string;
  outputFormat?: string;
  includePreview?: boolean;
}

export function restore(args: RestoreArgs, signal?: AbortSignal) {
  const fd = new FormData();
  fd.append('file', args.file);
  fd.append('ciphermap', args.ciphermap);
  fd.append('passphrase', args.passphrase);
  fd.append('include_preview', String(args.includePreview ?? true));
  if (args.outputFormat) fd.append('output_format', args.outputFormat);
  return postForm<RestoreResponse>('/restore', fd, signal);
}

/**
 * Independent isomorphism audit of an (original, sanitized, vault) triple.
 *
 * NOTE: `/api/v1/verify` requires THREE files: the confidential original, the
 * sanitized artifact, and the `.ciphermap`. It recomputes aggregates on both
 * sides rather than trusting the masking run's own fidelity report, which is
 * what makes it an *independent* audit.
 */
export interface VerifyArgs {
  original: File;
  sanitized: File;
  ciphermap: File;
  passphrase: string;
}

export interface VerifyCheck {
  check: string;
  ok: boolean;
  detail: string;
}

export interface VerifyResponse {
  passed: boolean;
  total_checks: number;
  failed_checks: number;
  checks: VerifyCheck[];
  schema_fingerprint: string | null;
}

export function verifyVault(args: VerifyArgs, signal?: AbortSignal) {
  const fd = new FormData();
  fd.append('original', args.original);
  fd.append('sanitized', args.sanitized);
  fd.append('ciphermap', args.ciphermap);
  fd.append('passphrase', args.passphrase);
  return postForm<VerifyResponse>('/verify', fd, signal);
}

/**
 * Dry-run transformation: shows the semantic projection and chart parity
 * WITHOUT producing a vault or a downloadable artifact. Lets an operator
 * audition a cover domain before committing a passphrase.
 */
export interface PreviewArgs {
  file: File;
  domainProfile: string;
  numericMode: NumericMode;
  seed?: string;
  rows?: number;
}

export interface PreviewResponse {
  table: string;
  domain_profile: string;
  profile_title: string;
  original: FramePreview;
  sanitized: FramePreview;
  column_map: Record<string, string>;
  column_strategies: Record<string, string>;
  sensitivity: Record<
    string,
    { severity: number; role: string; findings: string[] }
  >;
  fidelity: FidelityReportInfo;
  chart?: ChartBlock;
}

export function previewTransform(args: PreviewArgs, signal?: AbortSignal) {
  const fd = new FormData();
  fd.append('file', args.file);
  fd.append('domain_profile', args.domainProfile);
  fd.append('numeric_mode', args.numericMode);
  if (args.seed) fd.append('seed', args.seed);
  if (args.rows) fd.append('rows', String(args.rows));
  return postForm<PreviewResponse>('/preview', fd, signal);
}

/* -------------------------------------------------------------------------- */
/*  Local helpers (no network)                                                 */
/* -------------------------------------------------------------------------- */

/** Convert a base64 artifact payload into a Blob without touching the network. */
export function base64ToBlob(b64: string, mime: string): Blob {
  const binary = atob(b64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
  return new Blob([bytes], { type: mime });
}

/** Trigger a browser download from an in-memory blob URL. */
export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  // Revoke on the next frame so Safari has committed the navigation.
  requestAnimationFrame(() => URL.revokeObjectURL(url));
}

/** Download a base64 artifact returned by the API. */
export function downloadArtifact(artifact: {
  base64: string;
  mime_type: string;
  filename: string;
}): void {
  downloadBlob(
    base64ToBlob(artifact.base64, artifact.mime_type),
    artifact.filename,
  );
}

/** Serialise a `.ciphermap` manifest to an encrypted-at-rest JSON download. */
export function downloadManifest(
  manifest: Record<string, unknown>,
  filename: string,
): void {
  const blob = new Blob([JSON.stringify(manifest, null, 2)], {
    type: 'application/json',
  });
  downloadBlob(blob, filename);
}

/** Re-hydrate a downloaded manifest object into a File for the restore stage. */
export function manifestToFile(
  manifest: Record<string, unknown>,
  filename: string,
): File {
  return new File([JSON.stringify(manifest)], filename, {
    type: 'application/json',
  });
}
