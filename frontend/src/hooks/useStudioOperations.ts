import { useRef, type RefObject } from 'react';
import {
  ApiError,
  manifestToFile,
  obfuscate as apiObfuscate,
  previewTransform,
  profileDataset,
  restore as apiRestore,
  verifyVault,
} from '../lib/api';
import type { StudioState } from './useStudioState';

function formatApiError(e: unknown): string {
  if (e instanceof ApiError) return e.message;
  if (e instanceof Error) return e.message;
  return String(e);
}

async function execProfile(
  state: StudioState,
  signal: AbortSignal,
  target?: File,
) {
  const f = target ?? state.file;
  if (!f) return;
  state.setBusy('Profiling dataset in memory…');
  state.setError(null);
  try {
    const res = await profileDataset(f, state.datasetName || undefined, signal);
    state.setProfile(res);
    if (res.recommended_profile) state.setSelectedProfile(res.recommended_profile);
    state.go('profile');
    state.toasts.info(
      `Risk grade ${res.risk_grade}`,
      `Recommended cover domain: ${res.recommended_profile}`,
    );
  } catch (e) {
    if (!signal.aborted) {
      const msg = formatApiError(e);
      state.setError(msg);
      state.toasts.error('Profiling failed', msg);
    }
  } finally {
    if (!signal.aborted) state.setBusy(null);
  }
}

async function execObfuscate(state: StudioState, signal: AbortSignal) {
  if (!state.file) return;
  if (state.passphrase.length < 8) {
    state.setError('The vault passphrase must be at least 8 characters');
    return;
  }
  state.setBusy('Applying isomorphic transformation and sealing the vault…');
  state.setError(null);
  try {
    const res = await apiObfuscate(
      {
        file: state.file,
        passphrase: state.passphrase,
        domainProfile: state.selectedProfile,
        numericMode: state.numericMode,
        seed: state.seed || undefined,
        includePreview: true,
      },
      signal,
    );
    state.setResult(res);
    state.go('export');
    if (res.fidelity.passed) {
      state.toasts.success(
        'Vault sealed',
        `${res.fidelity.passed_checks}/${res.fidelity.total_checks} invariants verified · ${res.artifact.filename}`,
      );
    } else {
      state.toasts.warning(
        'Sealed with fidelity warnings',
        `${res.fidelity.failed_checks} invariant(s) did not hold`,
      );
    }
  } catch (e) {
    if (!signal.aborted) {
      const msg = formatApiError(e);
      state.setError(msg);
      state.toasts.error('Masking failed', msg);
    }
  } finally {
    if (!signal.aborted) state.setBusy(null);
  }
}

async function execRestore(state: StudioState, signal: AbortSignal) {
  if (!state.rFile || !state.rMap) {
    state.setError('Both the sanitized artifact and its .ciphermap vault are required');
    return;
  }
  state.setBusy('Unsealing vault and inverting bijection…');
  state.setError(null);
  try {
    const res = await apiRestore(
      {
        file: state.rFile,
        ciphermap: state.rMap,
        passphrase: state.rPassphrase,
        includePreview: true,
      },
      signal,
    );
    state.setRResult(res);
    state.toasts.success(
      'De-anonymization complete',
      `${res.statistics.values_restored} values restored across ${res.statistics.tables} table(s)`,
    );
  } catch (e) {
    if (!signal.aborted) {
      const msg = formatApiError(e);
      state.setError(msg);
      state.toasts.error('Restore failed', msg);
    }
  } finally {
    if (!signal.aborted) state.setBusy(null);
  }
}

async function execDryRun(state: StudioState, signal: AbortSignal) {
  if (!state.file) return;
  state.setBusy('Rehearsing projection in memory (no vault produced)…');
  state.setError(null);
  try {
    const res = await previewTransform(
      {
        file: state.file,
        domainProfile: state.selectedProfile,
        numericMode: state.numericMode,
        seed: state.seed || undefined,
      },
      signal,
    );
    state.setDryRun(res);
    state.setShowDryRun(true);
    state.toasts.success(
      'Dry run verified',
      `${res.fidelity.passed_checks}/${res.fidelity.total_checks} invariants hold`,
    );
  } catch (e) {
    if (!signal.aborted) {
      const msg = formatApiError(e);
      state.setError(msg);
      state.toasts.error('Dry run failed', msg);
    }
  } finally {
    if (!signal.aborted) state.setBusy(null);
  }
}

async function execAudit(state: StudioState, signal: AbortSignal) {
  if (!state.auditOriginal || !state.auditSanitized || !state.auditMap) return;
  state.setBusy('Recomputing invariants from raw files…');
  state.setError(null);
  try {
    const res = await verifyVault(
      {
        original: state.auditOriginal,
        sanitized: state.auditSanitized,
        ciphermap: state.auditMap,
        passphrase: state.auditPassphrase,
      },
      signal,
    );
    state.setAuditResult(res);
    if (res.passed) {
      state.toasts.success(
        'Independent audit passed',
        `${res.total_checks} recomputed checks agree`,
      );
    } else {
      state.toasts.warning(
        'Discrepancies identified',
        `${res.failed_checks} of ${res.total_checks} checks disagree`,
      );
    }
  } catch (e) {
    if (!signal.aborted) {
      const msg = formatApiError(e);
      state.setError(msg);
      state.toasts.error('Audit failed', msg);
    }
  } finally {
    if (!signal.aborted) state.setBusy(null);
  }
}

function execHandoff(state: StudioState) {
  if (!state.result) return;
  const artifactFile = new File(
    [Uint8Array.from(atob(state.result.artifact.base64), (c) => c.charCodeAt(0))],
    state.result.artifact.filename,
    { type: state.result.artifact.mime_type },
  );
  const mapFile = manifestToFile(
    state.result.ciphermap.manifest,
    state.result.ciphermap.filename,
  );
  state.setRFile(artifactFile);
  state.setRMap(mapFile);
  state.setRPassphrase(state.passphrase);
  state.go('restore');
  state.toasts.info(
    'Artifact loaded into restore',
    'The generated artifact and vault are ready for reverse verification',
  );
}

function execReset(state: StudioState, abortRef: RefObject<AbortController | null>) {
  abortRef.current?.abort();
  state.setFile(null);
  state.setDatasetName('');
  state.setProfile(null);
  state.setPassphrase('');
  state.setSeed('');
  state.setResult(null);
  state.setRFile(null);
  state.setRMap(null);
  state.setRPassphrase('');
  state.setRResult(null);
  state.setDryRun(null);
  state.setAuditOriginal(null);
  state.setAuditSanitized(null);
  state.setAuditMap(null);
  state.setAuditPassphrase('');
  state.setAuditResult(null);
  state.setError(null);
  state.setBusy(null);
  state.go('ingest');
  state.toasts.info('Workspace reset', 'All local buffers cleared from memory');
}

async function runWithSignal(
  state: StudioState,
  abortRef: RefObject<AbortController | null>,
  action: (s: StudioState, sig: AbortSignal) => Promise<void>,
) {
  abortRef.current?.abort();
  const ac = new AbortController();
  abortRef.current = ac;
  await action(state, ac.signal);
}

export function useStudioOperations(state: StudioState) {
  const abortRef = useRef<AbortController | null>(null);

  return {
    runProfile(target?: File) {
      abortRef.current?.abort();
      const ac = new AbortController();
      abortRef.current = ac;
      return execProfile(state, ac.signal, target);
    },
    runObfuscate() {
      return runWithSignal(state, abortRef, execObfuscate);
    },
    runRestore() {
      return runWithSignal(state, abortRef, execRestore);
    },
    runDryRun() {
      return runWithSignal(state, abortRef, execDryRun);
    },
    runAudit() {
      return runWithSignal(state, abortRef, execAudit);
    },
    handoffToRestore() {
      execHandoff(state);
    },
    resetAll() {
      execReset(state, abortRef);
    },
  };
}

export type StudioOperations = ReturnType<typeof useStudioOperations>;
