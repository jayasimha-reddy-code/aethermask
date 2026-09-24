/**
 * ============================================================================
 *  AetherMask (CipherShift) :: Data Studio
 * ============================================================================
 *  Offline, air-gapped console for semantic obfuscation, isomorphic
 *  masking, encrypted vaulting and lossless de-anonymization.
 *
 *  PIPELINE
 *  --------
 *    1. Ingest    - load local dataset (CSV/TSV/Parquet/XLSX/JSON/.sql)
 *    2. Profile   - offline sensitivity analysis and risk grading
 *    3. Transform - choose cover domain, mask, verify isomorphism
 *    4. Vault     - download sanitized artifact and AES-256-GCM ciphermap
 *    5. Restore   - de-anonymize losslessly from artifact + vault + passphrase
 *    6. Audit     - independent invariant re-verification from raw files
 * ============================================================================
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { AnimatePresence, m } from 'motion/react';
import {
  Activity,
  ArrowLeft,
  ArrowLeftRight,
  ArrowRight,
  CheckCircle2,
  Database,
  Download,
  FileDown,
  FileSearch,
  FileStack,
  Fingerprint,
  Layers,
  Lock,
  Play,
  RefreshCw,
  RotateCcw,
  ScanLine,
  ScanSearch,
  Search,
  ShieldCheck,
  Table2,
  Vault,
} from 'lucide-react';

import type {
  AttestationResponse,
  DomainProfileInfo,
  NumericMode,
  ObfuscateResponse,
  ProfileResponse,
  RestoreResponse,
  Stage,
} from '../lib/types';
import type { PreviewResponse, VerifyResponse } from '../lib/api';
import {
  ApiError,
  downloadArtifact,
  downloadManifest,
  fetchAttestation,
  fetchProfiles,
  manifestToFile,
  obfuscate as apiObfuscate,
  previewTransform,
  profileDataset,
  restore as apiRestore,
  verifyVault,
} from '../lib/api';
import { formatBytes, formatInt, shortHash } from '../lib/format';
import { easeQuick } from '../lib/motion';
import {
  useRevealVariants,
  useStageVariants,
} from '../lib/useReducedMotionVariants';
import { useEgressWatch } from '../lib/useEgressWatch';

import {
  Alert,
  Badge,
  Button,
  Copyable,
  EmptyState,
  Field,
  Panel,
  PanelHeader,
  Stat,
  inputClass,
} from './ui/Primitives';
import { DropZone, NumericModeToggle, PassphraseField, ProfilePicker } from './Controls';
import { ProfilePanel } from './ProfilePanel';
import { SplitCompare } from './SplitCompare';
import { ParityCharts } from './ParityCharts';
import { DataGrid } from './DataGrid';
import { AttestationDrawer } from './Attestation';
import { CommandPalette, useCommandPaletteHotkey, type Command } from './CommandPalette';
import { DryRunPreview } from './DryRunPreview';
import { AuditPanel } from './AuditPanel';
import { Kbd, useToasts } from './ui/Toasts';

/* -------------------------------------------------------------------------- */
/*  Stage metadata                                                             */
/* -------------------------------------------------------------------------- */

const STAGES: {
  id: Stage;
  label: string;
  Icon: typeof Database;
  blurb: string;
}[] = [
  { id: 'ingest', label: 'Ingest', Icon: Database, blurb: 'Load source dataset' },
  { id: 'profile', label: 'Profile', Icon: ScanSearch, blurb: 'Analyze sensitivity' },
  { id: 'transform', label: 'Transform', Icon: ArrowLeftRight, blurb: 'Cover domain projection' },
  { id: 'export', label: 'Vault', Icon: Vault, blurb: 'Cryptographic vault' },
  { id: 'restore', label: 'Restore', Icon: RotateCcw, blurb: 'Lossless de-anonymization' },
  { id: 'audit', label: 'Audit', Icon: ScanLine, blurb: 'Independent verification' },
];

const STAGE_INDEX: Record<Stage, number> = {
  ingest: 0,
  profile: 1,
  transform: 2,
  export: 3,
  restore: 4,
  audit: 5,
};

const ACCEPT_DATA = '.csv,.tsv,.parquet,.xlsx,.xls,.json,.sql,.txt';
const ACCEPT_MAP = '.ciphermap,.json';

/* ========================================================================== */
/*  Stage rail                                                                 */
/* ========================================================================== */

function StageRail({
  stage,
  onJump,
  reachable,
}: {
  stage: Stage;
  onJump: (s: Stage) => void;
  reachable: Set<Stage>;
}) {
  return (
    <nav aria-label="Pipeline stage" className="w-full">
      <ol className="flex items-stretch gap-2 overflow-x-auto pb-1">
        {STAGES.map(({ id, label, Icon, blurb }, i) => {
          const active = id === stage;
          const done = STAGE_INDEX[id] < STAGE_INDEX[stage];
          const available = reachable.has(id);
          return (
            <li key={id} className="min-w-0 flex-1">
              <button
                type="button"
                onClick={() => available && onJump(id)}
                disabled={!available}
                aria-current={active ? 'step' : undefined}
                className={`relative flex w-full items-center gap-2.5 overflow-hidden rounded-lg border px-3 py-2 text-left outline-none transition-colors duration-150 ${
                  active
                    ? 'border-signal-500/40 bg-signal-500/8'
                    : available
                      ? 'cursor-pointer border-white/8 bg-abyss-850/60 hover:border-white/16 hover:bg-abyss-800/60'
                      : 'cursor-not-allowed border-white/4 bg-abyss-900/30 opacity-40'
                }`}
              >
                {active ? (
                  <span
                    className="absolute inset-x-0 bottom-0 h-0.5 bg-signal-500"
                    aria-hidden="true"
                  />
                ) : null}

                <span
                  className={`flex size-6 shrink-0 items-center justify-center rounded-md ${
                    active
                      ? 'bg-signal-500 text-abyss-950 font-medium'
                      : done
                        ? 'bg-signal-500/15 text-signal-400'
                        : 'bg-abyss-800 text-slate-500'
                  }`}
                  aria-hidden="true"
                >
                  {done && !active ? (
                    <CheckCircle2 size={13} />
                  ) : (
                    <Icon size={13} />
                  )}
                </span>

                <span className="min-w-0 flex-1">
                  <span
                    className={`block truncate text-xs font-medium ${
                      active ? 'text-signal-400' : 'text-slate-200'
                    }`}
                  >
                    <span className="tabular mr-1 text-slate-500">{i + 1}</span>
                    {label}
                  </span>
                  <span className="hidden truncate text-[11px] text-slate-500 lg:block">
                    {blurb}
                  </span>
                </span>
              </button>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

/* ========================================================================== */
/*  Main component                                                             */
/* ========================================================================== */

export default function DataStudio() {
  /* ---- pipeline state ---- */
  const [stage, setStage] = useState<Stage>('ingest');
  const [direction, setDirection] = useState(1);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  /* ---- data state ---- */
  const [file, setFile] = useState<File | null>(null);
  const [datasetName, setDatasetName] = useState('');
  const [profile, setProfile] = useState<ProfileResponse | null>(null);
  const [profiles, setProfiles] = useState<DomainProfileInfo[]>([]);
  const [attestation, setAttestation] = useState<AttestationResponse | null>(null);
  const [showAttestation, setShowAttestation] = useState(false);

  /* ---- transform config ---- */
  const [selectedProfile, setSelectedProfile] = useState('defense_to_logistics');
  const [numericMode, setNumericMode] = useState<NumericMode>('identity');
  const [passphrase, setPassphrase] = useState('');
  const [seed, setSeed] = useState('');
  const [result, setResult] = useState<ObfuscateResponse | null>(null);

  /* ---- restore state ---- */
  const [rFile, setRFile] = useState<File | null>(null);
  const [rMap, setRMap] = useState<File | null>(null);
  const [rPassphrase, setRPassphrase] = useState('');
  const [rResult, setRResult] = useState<RestoreResponse | null>(null);

  /* ---- dry run (POST /preview - no vault produced) ---- */
  const [dryRun, setDryRun] = useState<PreviewResponse | null>(null);
  const [showDryRun, setShowDryRun] = useState(false);

  /* ---- independent audit (POST /verify - 3 files) ---- */
  const [auditOriginal, setAuditOriginal] = useState<File | null>(null);
  const [auditSanitized, setAuditSanitized] = useState<File | null>(null);
  const [auditMap, setAuditMap] = useState<File | null>(null);
  const [auditPassphrase, setAuditPassphrase] = useState('');
  const [auditResult, setAuditResult] = useState<VerifyResponse | null>(null);

  /* ---- command palette ---- */
  const [paletteOpen, setPaletteOpen] = useState(false);

  const egress = useEgressWatch();
  const toasts = useToasts();
  const abortRef = useRef<AbortController | null>(null);

  /* ---- motion-aware variants ---- */
  const stageVariants = useStageVariants();
  const revealVariants = useRevealVariants();

  /* ---- bootstrap: catalogue + attestation ---- */
  useEffect(() => {
    const ac = new AbortController();
    void (async () => {
      try {
        const [cat, att] = await Promise.all([
          fetchProfiles(ac.signal),
          fetchAttestation(ac.signal),
        ]);
        setProfiles(cat.profiles);
        setAttestation(att);
        if (cat.profiles.length > 0 && !cat.profiles.some((p) => p.key === selectedProfile)) {
          setSelectedProfile(cat.profiles[0].key);
        }
      } catch (e) {
        if (!ac.signal.aborted) {
          setError(
            e instanceof Error
              ? `Could not reach the local AetherMask service: ${e.message}`
              : 'Could not reach the local AetherMask service',
          );
        }
      }
    })();
    return () => ac.abort();
  }, []);

  /* ---- transient notices auto-clear ---- */
  useEffect(() => {
    if (!notice) return undefined;
    const t = window.setTimeout(() => setNotice(null), 4200);
    return () => window.clearTimeout(t);
  }, [notice]);

  const go = useCallback((next: Stage) => {
    setStage((current) => {
      setDirection(STAGE_INDEX[next] >= STAGE_INDEX[current] ? 1 : -1);
      return next;
    });
    setError(null);
  }, []);

  const reachable = useMemo(() => {
    const set = new Set<Stage>(['ingest', 'restore', 'audit']);
    if (profile) set.add('profile');
    if (file) set.add('transform');
    if (result) set.add('export');
    return set;
  }, [file, profile, result]);

  const describeError = (e: unknown): string => {
    if (e instanceof ApiError) return `${e.message} (HTTP ${e.status})`;
    if (e instanceof Error) return e.message;
    return String(e);
  };

  /* ---------------------------------------------------------------------- */
  /*  Actions                                                                */
  /* ---------------------------------------------------------------------- */

  const runProfile = useCallback(
    async (target?: File) => {
      const f = target ?? file;
      if (!f) return;
      abortRef.current?.abort();
      const ac = new AbortController();
      abortRef.current = ac;
      setBusy('Profiling dataset in memory…');
      setError(null);
      try {
        const res = await profileDataset(f, datasetName || undefined, ac.signal);
        setProfile(res);
        if (res.recommended_profile) setSelectedProfile(res.recommended_profile);
        go('profile');
        toasts.info(
          `Risk grade ${res.risk_grade}`,
          `Recommended cover domain: ${res.recommended_profile}`,
        );
      } catch (e) {
        if (!ac.signal.aborted) {
          const msg = describeError(e);
          setError(msg);
          toasts.error('Profiling failed', msg);
        }
      } finally {
        if (!ac.signal.aborted) setBusy(null);
      }
    },
    [file, datasetName, go, toasts],
  );

  const runObfuscate = useCallback(async () => {
    if (!file) return;
    if (passphrase.length < 8) {
      setError('The vault passphrase must be at least 8 characters');
      return;
    }
    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;
    setBusy('Applying isomorphic transformation and sealing the vault…');
    setError(null);
    try {
      const res = await apiObfuscate(
        {
          file,
          passphrase,
          domainProfile: selectedProfile,
          numericMode,
          seed: seed || undefined,
          includePreview: true,
        },
        ac.signal,
      );
      setResult(res);
      go('export');
      if (res.fidelity.passed) {
        toasts.success(
          'Vault sealed',
          `${res.fidelity.passed_checks}/${res.fidelity.total_checks} invariants verified · ${res.artifact.filename}`,
        );
      } else {
        toasts.warning(
          'Sealed with fidelity warnings',
          `${res.fidelity.failed_checks} invariant(s) did not hold`,
        );
      }
    } catch (e) {
      if (!ac.signal.aborted) {
        const msg = describeError(e);
        setError(msg);
        toasts.error('Masking failed', msg);
      }
    } finally {
      if (!ac.signal.aborted) setBusy(null);
    }
  }, [file, passphrase, selectedProfile, numericMode, seed, go, toasts]);

  const runRestore = useCallback(async () => {
    if (!rFile || !rMap) {
      setError('Both the sanitized artifact and its .ciphermap vault are required');
      return;
    }
    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;
    setBusy('Unsealing vault and inverting bijection…');
    setError(null);
    try {
      const res = await apiRestore(
        { file: rFile, ciphermap: rMap, passphrase: rPassphrase, includePreview: true },
        ac.signal,
      );
      setRResult(res);
      toasts.success(
        'De-anonymization complete',
        `${res.statistics.values_restored} values restored across ${res.statistics.tables} table(s)`,
      );
    } catch (e) {
      if (!ac.signal.aborted) {
        const msg = describeError(e);
        setError(msg);
        toasts.error('Restore failed', msg);
      }
    } finally {
      if (!ac.signal.aborted) setBusy(null);
    }
  }, [rFile, rMap, rPassphrase, toasts]);

  const runDryRun = useCallback(async () => {
    if (!file) return;
    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;
    setBusy('Rehearsing projection in memory (no vault produced)…');
    setError(null);
    try {
      const res = await previewTransform(
        {
          file,
          domainProfile: selectedProfile,
          numericMode,
          seed: seed || undefined,
        },
        ac.signal,
      );
      setDryRun(res);
      setShowDryRun(true);
      toasts.success(
        'Dry run verified',
        `${res.fidelity.passed_checks}/${res.fidelity.total_checks} invariants hold`,
      );
    } catch (e) {
      if (!ac.signal.aborted) {
        const msg = describeError(e);
        setError(msg);
        toasts.error('Dry run failed', msg);
      }
    } finally {
      if (!ac.signal.aborted) setBusy(null);
    }
  }, [file, selectedProfile, numericMode, seed, toasts]);

  const runAudit = useCallback(async () => {
    if (!auditOriginal || !auditSanitized || !auditMap) return;
    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;
    setBusy('Recomputing invariants from raw files…');
    setError(null);
    try {
      const res = await verifyVault(
        {
          original: auditOriginal,
          sanitized: auditSanitized,
          ciphermap: auditMap,
          passphrase: auditPassphrase,
        },
        ac.signal,
      );
      setAuditResult(res);
      if (res.passed) {
        toasts.success(
          'Independent audit passed',
          `${res.total_checks} recomputed checks agree`,
        );
      } else {
        toasts.warning(
          'Discrepancies identified',
          `${res.failed_checks} of ${res.total_checks} checks disagree`,
        );
      }
    } catch (e) {
      if (!ac.signal.aborted) {
        const msg = describeError(e);
        setError(msg);
        toasts.error('Audit failed', msg);
      }
    } finally {
      if (!ac.signal.aborted) setBusy(null);
    }
  }, [auditOriginal, auditSanitized, auditMap, auditPassphrase, toasts]);

  const handoffToRestore = useCallback(() => {
    if (!result) return;
    const artifactFile = new File(
      [
        Uint8Array.from(atob(result.artifact.base64), (c) => c.charCodeAt(0)),
      ],
      result.artifact.filename,
      { type: result.artifact.mime_type },
    );
    setRFile(artifactFile);
    setRMap(manifestToFile(result.ciphermap.manifest, result.ciphermap.filename));
    setRPassphrase(passphrase);
    setRResult(null);
    go('restore');
    setNotice(
      'Artifact and vault loaded into restore stage. Press “Re-identify” to verify round-trip.',
    );
  }, [result, passphrase, go]);

  const resetAll = useCallback(() => {
    abortRef.current?.abort();
    setFile(null);
    setDatasetName('');
    setProfile(null);
    setResult(null);
    setRFile(null);
    setRMap(null);
    setRResult(null);
    setPassphrase('');
    setRPassphrase('');
    setSeed('');
    setError(null);
    setBusy(null);
    setDryRun(null);
    setShowDryRun(false);
    setAuditOriginal(null);
    setAuditSanitized(null);
    setAuditMap(null);
    setAuditPassphrase('');
    setAuditResult(null);
    go('ingest');
    toasts.info('Session reset', 'All in-memory buffers discarded');
  }, [go, toasts]);

  /* ---------------------------------------------------------------------- */
  /*  Command palette                                                        */
  /* ---------------------------------------------------------------------- */

  useCommandPaletteHotkey(() => setPaletteOpen(true));

  const commands = useMemo<Command[]>(() => {
    const nav: Command[] = STAGES.map(({ id, label, Icon, blurb }) => ({
      id: `go-${id}`,
      group: 'Navigate',
      label: `Go to ${label}`,
      hint: blurb,
      icon: <Icon size={13} />,
      disabled: !reachable.has(id),
      keywords: `${id} stage ${blurb}`,
      run: () => go(id),
    }));

    const actions: Command[] = [
      {
        id: 'act-profile',
        group: 'Actions',
        label: 'Analyse sensitivity',
        hint: 'Offline risk grading of the loaded dataset',
        icon: <ScanSearch size={13} />,
        disabled: !file || busy !== null,
        keywords: 'profile scan risk grade sensitivity',
        run: () => void runProfile(),
      },
      {
        id: 'act-dryrun',
        group: 'Actions',
        label: 'Run dry run (no vault)',
        hint: 'Audition the projection without sealing anything',
        icon: <Play size={13} />,
        disabled: !file || busy !== null,
        keywords: 'preview rehearse dry run audition',
        run: () => {
          go('transform');
          setShowDryRun(true);
          void runDryRun();
        },
      },
      {
        id: 'act-mask',
        group: 'Actions',
        label: 'Mask & seal vault',
        hint: 'Apply transformation and encrypt mapping',
        icon: <Lock size={13} />,
        disabled: !file || passphrase.length < 8 || busy !== null,
        keywords: 'obfuscate mask seal encrypt vault',
        run: () => void runObfuscate(),
      },
      {
        id: 'act-restore',
        group: 'Actions',
        label: 'Re-identify dataset',
        hint: 'Reverse transformation losslessly',
        icon: <RotateCcw size={13} />,
        disabled: !rFile || !rMap || rPassphrase.length < 8 || busy !== null,
        keywords: 'restore reverse deanonymize re-identify',
        run: () => {
          go('restore');
          void runRestore();
        },
      },
      {
        id: 'act-audit',
        group: 'Actions',
        label: 'Run independent audit',
        hint: 'Recompute invariants directly from raw files',
        icon: <ScanLine size={13} />,
        disabled:
          !auditOriginal ||
          !auditSanitized ||
          !auditMap ||
          auditPassphrase.length < 8 ||
          busy !== null,
        keywords: 'verify audit independent check isomorphism',
        run: () => {
          go('audit');
          void runAudit();
        },
      },
    ];

    const exports: Command[] = result
      ? [
          {
            id: 'dl-artifact',
            group: 'Export',
            label: 'Download sanitized artifact',
            hint: result.artifact.filename,
            icon: <Download size={13} />,
            keywords: 'download export artifact csv output',
            run: () => downloadArtifact(result.artifact),
          },
          {
            id: 'dl-vault',
            group: 'Export',
            label: 'Download .ciphermap vault',
            hint: result.ciphermap.filename,
            icon: <Vault size={13} />,
            keywords: 'download vault ciphermap key mapping',
            run: () =>
              downloadManifest(result.ciphermap.manifest, result.ciphermap.filename),
          },
          {
            id: 'handoff',
            group: 'Export',
            label: 'Verify round-trip',
            hint: 'Load artifact and vault into restore stage',
            icon: <RotateCcw size={13} />,
            keywords: 'roundtrip handoff verify restore',
            run: handoffToRestore,
          },
        ]
      : [];

    const system: Command[] = [
      {
        id: 'sys-attest',
        group: 'System',
        label: 'Open air-gap attestation',
        hint: `${egress.external.length} external call(s) observed`,
        icon: <ShieldCheck size={13} />,
        keywords: 'attestation airgap offline egress network proof',
        run: () => setShowAttestation(true),
      },
      {
        id: 'sys-reset',
        group: 'System',
        label: 'Reset session',
        hint: 'Discard all in-memory buffers',
        icon: <RefreshCw size={13} />,
        keywords: 'reset clear wipe discard new',
        run: resetAll,
      },
    ];

    return [...nav, ...actions, ...exports, ...system];
  }, [
    reachable, go, file, busy, passphrase, rFile, rMap, rPassphrase,
    auditOriginal, auditSanitized, auditMap, auditPassphrase, result,
    egress.external.length, runProfile, runDryRun, runObfuscate, runRestore,
    runAudit, handoffToRestore, resetAll,
  ]);

  /* ---------------------------------------------------------------------- */
  /*  Render                                                                 */
  /* ---------------------------------------------------------------------- */

  return (
    <div className="min-h-screen bg-abyss-950 text-slate-100">
      {/* ---------------------------------------------------------------- */}
      {/*  Header                                                           */}
      {/* ---------------------------------------------------------------- */}
      <header className="sticky top-0 z-40 border-b border-white/8 bg-abyss-950/90 backdrop-blur-md">
        <div className="mx-auto flex max-w-[1600px] flex-wrap items-center justify-between gap-3 px-6 py-3.5">
          <div className="flex items-center gap-3">
            <span
              className="flex size-8 items-center justify-center rounded-lg border border-white/8 bg-abyss-900 text-signal-400"
              aria-hidden="true"
            >
              <Layers size={16} />
            </span>
            <div>
              <h1 className="text-sm font-medium leading-tight text-slate-100">
                AetherMask{' '}
                <span className="font-normal text-slate-500">· CipherShift</span>
              </h1>
              <p className="text-xs text-slate-400">
                Offline semantic obfuscation &amp; lossless de-anonymization
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setPaletteOpen(true)}
              className="hidden items-center gap-2 rounded-lg border border-white/8 bg-abyss-850 px-2.5 py-1.5 text-xs text-slate-300 outline-none hover:border-white/16 hover:bg-abyss-800 transition-colors sm:flex"
              title="Open command palette"
              aria-keyshortcuts="Control+K Meta+K"
            >
              <Search size={13} className="text-slate-400" aria-hidden="true" />
              <span>Commands</span>
              <Kbd>Ctrl K</Kbd>
            </button>

            <button
              type="button"
              onClick={() => setShowAttestation(true)}
              className="flex items-center gap-2 rounded-lg border border-white/8 bg-abyss-850 px-2.5 py-1.5 text-xs font-normal text-slate-300 outline-none hover:border-white/16 hover:bg-abyss-800 transition-colors"
              title="Open air-gap attestation report"
            >
              <span
                className={`size-1.5 rounded-full ${
                  egress.external.length === 0 ? 'bg-signal-400' : 'bg-classified-400'
                }`}
                aria-hidden="true"
              />
              <ShieldCheck size={13} className="text-slate-400" aria-hidden="true" />
              <span>
                {egress.external.length === 0
                  ? 'Air-gapped'
                  : `${egress.external.length} external call(s)`}
              </span>
            </button>

            <Button tone="ghost" icon={<RefreshCw size={13} />} onClick={resetAll}>
              Reset
            </Button>
          </div>
        </div>

        <div className="mx-auto max-w-[1600px] px-6 pb-3">
          <StageRail stage={stage} onJump={go} reachable={reachable} />
        </div>
      </header>

      {/* ---------------------------------------------------------------- */}
      {/*  Status strip                                                     */}
      {/* ---------------------------------------------------------------- */}
      <div className="mx-auto max-w-[1600px] px-6">
        <AnimatePresence mode="popLayout">
          {busy ? (
            <m.div
              key="busy"
              variants={revealVariants}
              initial="hidden"
              animate="visible"
              exit="exit"
              className="mt-4 flex items-center gap-3 rounded-xl border border-signal-500/20 bg-signal-500/5 px-4 py-2.5"
              role="status"
              aria-live="polite"
            >
              <Activity size={14} className="shrink-0 text-signal-400" aria-hidden="true" />
              <span className="text-xs text-signal-400">{busy}</span>
            </m.div>
          ) : null}

          {error ? (
            <m.div key="error" className="mt-4" layout>
              <Alert tone="error" title="Operation failed" onDismiss={() => setError(null)}>
                {error}
              </Alert>
            </m.div>
          ) : null}

          {notice ? (
            <m.div key="notice" className="mt-4" layout>
              <Alert tone="info" title="Ready" onDismiss={() => setNotice(null)}>
                {notice}
              </Alert>
            </m.div>
          ) : null}
        </AnimatePresence>
      </div>

      {/* ---------------------------------------------------------------- */}
      {/*  Stage content                                                    */}
      {/* ---------------------------------------------------------------- */}
      <main className="mx-auto max-w-[1600px] px-6 py-6">
        <AnimatePresence mode="wait" custom={direction} initial={false}>
          <m.div
            key={stage}
            custom={direction}
            variants={stageVariants}
            initial="enter"
            animate="center"
            exit="exit"
          >
            {/* ============================ INGEST ============================ */}
            {stage === 'ingest' ? (
              <div className="grid gap-6 lg:grid-cols-[minmax(0,1.15fr)_minmax(0,0.85fr)]">
                <Panel>
                  <PanelHeader
                    icon={<Database size={15} />}
                    title="1 · Ingest source dataset"
                    subtitle="Parsed in local memory and never persisted or transmitted"
                  />
                  <div className="space-y-4 p-5">
                    <DropZone
                      file={file}
                      onFile={(f) => {
                        setFile(f);
                        setProfile(null);
                        setResult(null);
                        if (f && !datasetName) {
                          setDatasetName(f.name.replace(/\.[^.]+$/, ''));
                        }
                      }}
                      accept={ACCEPT_DATA}
                      label="Drop a dataset here, or click to browse"
                      hint="CSV · TSV · Parquet · XLSX · XLS · JSON · .sql dump"
                    />

                    <Field
                      label="Dataset name"
                      htmlFor="dataset-name"
                      hint="Labels tables and the emitted artifact"
                    >
                      <input
                        id="dataset-name"
                        type="text"
                        value={datasetName}
                        onChange={(e) => setDatasetName(e.target.value)}
                        placeholder="e.g. classified_missions"
                        className={inputClass}
                      />
                    </Field>

                    <div className="flex flex-wrap gap-2 pt-1">
                      <Button
                        tone="primary"
                        icon={<ScanSearch size={14} />}
                        disabled={!file}
                        busy={busy !== null}
                        onClick={() => void runProfile()}
                      >
                        Analyse sensitivity
                      </Button>
                      <Button
                        tone="neutral"
                        icon={<ArrowRight size={14} />}
                        disabled={!file}
                        onClick={() => go('transform')}
                      >
                        Skip to transform
                      </Button>
                    </div>
                  </div>
                </Panel>

                <div className="space-y-5">
                  <Panel>
                    <PanelHeader
                      icon={<ShieldCheck size={15} />}
                      title="Offline verification guarantees"
                      subtitle="Enforced by architecture and air-gap sentinel"
                    />
                    <ul className="space-y-2.5 p-5">
                      {[
                        {
                          Icon: ShieldCheck,
                          title: 'Zero external network calls',
                          body: 'No LLM APIs, external fonts, telemetry or CDNs. Browser egress watchdog halts any outbound attempt.',
                        },
                        {
                          Icon: Activity,
                          title: 'Mathematical isomorphism',
                          body: 'Categorical multisets, cardinality, null topologies and query aggregates are provably preserved.',
                        },
                        {
                          Icon: Fingerprint,
                          title: 'Deterministic bijectivity',
                          body: 'Every entity maps one-to-one without many-to-one collisions, guaranteeing lossless inversion.',
                        },
                        {
                          Icon: Lock,
                          title: 'Cryptographic vault',
                          body: 'Argon2id key derivation, HMAC-SHA256 integrity, AES-256-GCM cipher with schema binding.',
                        },
                      ].map(({ Icon, title, body }) => (
                        <li
                          key={title}
                          className="flex gap-3 rounded-lg border border-white/8 bg-abyss-850/50 p-3"
                        >
                          <Icon
                            size={14}
                            className="mt-0.5 shrink-0 text-slate-400"
                            aria-hidden="true"
                          />
                          <div>
                            <div className="text-xs font-medium text-slate-200">
                              {title}
                            </div>
                            <p className="mt-0.5 text-xs leading-relaxed text-slate-400">
                              {body}
                            </p>
                          </div>
                        </li>
                      ))}
                    </ul>
                  </Panel>

                  {attestation?.lexicon ? (
                    <Panel>
                      <PanelHeader
                        icon={<FileStack size={15} />}
                        title="Local lexicon capacity"
                        subtitle="Deterministic surrogate pools vendored within the air-gap"
                      />
                      <div className="grid grid-cols-2 gap-3 p-5">
                        <Stat
                          label="Cover domains"
                          value={formatInt(attestation.lexicon.profiles)}
                        />
                        <Stat
                          label="Surrogate entities"
                          value={formatInt(attestation.lexicon.total_unique_surrogates)}
                        />
                        <Stat
                          label="Token shift rules"
                          value={formatInt(attestation.lexicon.total_token_shift_rules)}
                        />
                        <Stat
                          label="Pattern detectors"
                          value={`${formatInt(attestation.lexicon.sensitivity_rules)} + ${formatInt(attestation.lexicon.ner_patterns)}`}
                          hint="Sensitivity + offline NER"
                        />
                      </div>
                    </Panel>
                  ) : null}
                </div>
              </div>
            ) : null}

            {/* ============================ PROFILE =========================== */}
            {stage === 'profile' ? (
              <Panel>
                <PanelHeader
                  icon={<ScanSearch size={15} />}
                  title="2 · Sensitivity profile"
                  subtitle="Rule-based offline inspection with evidence fragments redacted"
                  actions={
                    <div className="flex gap-2">
                      <Button tone="ghost" icon={<ArrowLeft size={13} />} onClick={() => go('ingest')}>
                        Back
                      </Button>
                      <Button
                        tone="primary"
                        icon={<ArrowRight size={13} />}
                        onClick={() => go('transform')}
                      >
                        Configure transform
                      </Button>
                    </div>
                  }
                />
                <div className="p-5">
                  {profile ? (
                    <ProfilePanel profile={profile} />
                  ) : (
                    <EmptyState icon={<FileSearch size={20} />} title="No profile generated">
                      Return to ingest and run “Analyse sensitivity”.
                    </EmptyState>
                  )}
                </div>
              </Panel>
            ) : null}

            {/* =========================== TRANSFORM ========================== */}
            {stage === 'transform' ? (
              <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_380px]">
                <Panel>
                  <PanelHeader
                    icon={<ArrowLeftRight size={15} />}
                    title="3 · Isomorphic transformation"
                    subtitle="Select the target non-classified cover domain"
                  />
                  <div className="space-y-6 p-5">
                    <div>
                      <h3 className="mb-2 text-xs font-medium text-slate-300">
                        Cover domain profile
                      </h3>
                      {profiles.length > 0 ? (
                        <ProfilePicker
                          profiles={profiles}
                          selected={selectedProfile}
                          onSelect={setSelectedProfile}
                          recommended={profile?.recommended_profile}
                        />
                      ) : (
                        <div className="rounded-lg border border-white/8 bg-abyss-850/50 p-6 text-center text-xs text-slate-500">
                          Loading local profile catalogue…
                        </div>
                      )}
                    </div>

                    <div>
                      <h3 className="mb-2 text-xs font-medium text-slate-300">
                        Numbers &amp; coordinates
                      </h3>
                      <NumericModeToggle mode={numericMode} onChange={setNumericMode} />
                    </div>

                    <div className="hairline" />

                    <div>
                      <div className="mb-2 flex items-center justify-between gap-3">
                        <h3 className="text-xs font-medium text-slate-300">
                          Dry-run rehearsal
                        </h3>
                        <button
                          type="button"
                          onClick={() => setShowDryRun((v) => !v)}
                          aria-expanded={showDryRun}
                          className="text-xs text-slate-400 outline-none hover:text-slate-200 transition-colors"
                        >
                          {showDryRun ? 'Hide' : 'Show preview'}
                        </button>
                      </div>
                      <AnimatePresence initial={false}>
                        {showDryRun ? (
                          <m.div
                            key="dryrun"
                            initial={{ height: 0, opacity: 0 }}
                            animate={{ height: 'auto', opacity: 1 }}
                            exit={{ height: 0, opacity: 0 }}
                            transition={easeQuick}
                            className="overflow-hidden"
                          >
                            <DryRunPreview
                              preview={dryRun}
                              busy={busy !== null}
                              canRun={!!file && busy === null}
                              onRun={() => void runDryRun()}
                              profileTitle={
                                profiles.find((p) => p.key === selectedProfile)?.title ?? ''
                              }
                            />
                          </m.div>
                        ) : null}
                      </AnimatePresence>
                    </div>
                  </div>
                </Panel>

                <Panel>
                  <PanelHeader
                    icon={<Lock size={15} />}
                    title="Vault configuration"
                    subtitle="Passphrase remains exclusively in volatile memory"
                  />
                  <div className="space-y-4 p-5">
                    <div className="rounded-lg border border-white/8 bg-abyss-850/60 p-3">
                      <div className="text-xs text-slate-500">
                        Source dataset
                      </div>
                      <div className="tabular mt-0.5 truncate text-xs font-medium text-slate-200">
                        {file ? file.name : '— none selected —'}
                      </div>
                      {file ? (
                        <div className="mt-0.5 text-xs text-slate-500">
                          {formatBytes(file.size)}
                        </div>
                      ) : null}
                    </div>

                    <PassphraseField value={passphrase} onChange={setPassphrase} />

                    <Field
                      label="Determinism seed (optional)"
                      htmlFor="seed"
                      hint="Identical seed and profile yield bit-exact reproducible output"
                    >
                      <input
                        id="seed"
                        type="text"
                        value={seed}
                        onChange={(e) => setSeed(e.target.value)}
                        placeholder="e.g. exercise-alpha-2026"
                        spellCheck={false}
                        className={inputClass}
                      />
                    </Field>

                    <div className="hairline" />

                    <div className="flex flex-col gap-2 pt-1">
                      <Button
                        tone="primary"
                        icon={<Lock size={14} />}
                        disabled={!file || passphrase.length < 8}
                        busy={busy !== null}
                        onClick={() => void runObfuscate()}
                        className="w-full"
                      >
                        Mask &amp; seal vault
                      </Button>
                      <Button
                        tone="ghost"
                        icon={<ArrowLeft size={13} />}
                        onClick={() => go(profile ? 'profile' : 'ingest')}
                      >
                        Back
                      </Button>
                    </div>
                  </div>
                </Panel>
              </div>
            ) : null}

            {/* ============================ EXPORT ============================ */}
            {stage === 'export' && result ? (
              <div className="space-y-5">
                {/* Fidelity verdict */}
                <Panel className="border-signal-500/30 bg-signal-500/5">
                  <div className="flex flex-wrap items-center justify-between gap-4 p-5">
                    <div className="flex items-center gap-3.5">
                      <span className="flex size-9 items-center justify-center rounded-lg border border-signal-500/30 bg-signal-500/10 text-signal-400">
                        <CheckCircle2 size={18} />
                      </span>
                      <div>
                        <div className="text-sm font-medium text-signal-400">
                          {result.fidelity.passed
                            ? 'Isomorphism verified'
                            : 'Fidelity warnings identified'}
                        </div>
                        <p className="mt-0.5 text-xs text-slate-400">
                          {formatInt(result.fidelity.passed_checks)} of{' '}
                          {formatInt(result.fidelity.total_checks)} invariants verified ·{' '}
                          {result.profile_title}
                        </p>
                      </div>
                    </div>

                    <div className="flex flex-wrap gap-2">
                      <Button
                        tone="primary"
                        icon={<Download size={14} />}
                        onClick={() => downloadArtifact(result.artifact)}
                      >
                        Sanitized artifact
                      </Button>
                      <Button
                        tone="neutral"
                        icon={<Vault size={14} />}
                        onClick={() =>
                          downloadManifest(
                            result.ciphermap.manifest,
                            result.ciphermap.filename,
                          )
                        }
                      >
                        .ciphermap vault
                      </Button>
                      <Button
                        tone="neutral"
                        icon={<RotateCcw size={14} />}
                        onClick={handoffToRestore}
                      >
                        Verify round-trip
                      </Button>
                    </div>
                  </div>

                  {result.fidelity.failures.length > 0 ? (
                    <div className="border-t border-white/8 px-5 py-3">
                      <ul className="space-y-1">
                        {result.fidelity.failures.map((f, i) => (
                          <li key={i} className="text-xs text-classified-400">
                            • {f}
                          </li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                </Panel>

                {/* Key statistics */}
                <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
                  <Stat
                    label="Rows masked"
                    value={formatInt(result.statistics.total_rows)}
                    icon={<Table2 size={13} />}
                  />
                  <Stat
                    label="Columns renamed"
                    value={formatInt(result.statistics.columns_renamed)}
                  />
                  <Stat
                    label="Values substituted"
                    value={formatInt(result.statistics.values_substituted)}
                  />
                  <Stat
                    label="Artifact size"
                    value={formatBytes(result.artifact.size_bytes)}
                    hint={result.artifact.filename}
                  />
                </div>

                {/* Integrity identifiers */}
                <Panel>
                  <PanelHeader
                    icon={<Fingerprint size={15} />}
                    title="Cryptographic integrity bindings"
                    subtitle="Binds artifact to vault; mismatches reject at de-anonymization"
                  />
                  <div className="flex flex-wrap gap-2 p-5">
                    <Copyable
                      value={result.artifact.sha256}
                      display={`Artifact SHA256 · ${shortHash(result.artifact.sha256)}`}
                    />
                    <Copyable
                      value={result.schema_fingerprint}
                      display={`Schema fingerprint · ${shortHash(result.schema_fingerprint)}`}
                    />
                    <Badge tone="muted">
                      <Lock size={10} aria-hidden="true" />
                      {String(
                        (result.ciphermap.manifest as Record<string, unknown>)
                          .cipher_suite ?? 'AES-256-GCM',
                      )}
                    </Badge>
                    <Badge tone="muted">{result.domain_profile}</Badge>
                  </div>
                </Panel>

                {/* Parity proof */}
                {result.preview?.chart ? (
                  <Panel>
                    <PanelHeader
                      icon={<Activity size={15} />}
                      title="Analytical parity proof"
                      subtitle="Simultaneous execution of identical query against both relations"
                    />
                    <div className="p-5">
                      <ParityCharts chart={result.preview.chart} />
                    </div>
                  </Panel>
                ) : null}

                {/* Split comparison */}
                {result.preview ? (
                  <Panel>
                    <PanelHeader
                      icon={<Table2 size={15} />}
                      title="Confidential ↔ sanitized comparison"
                      subtitle="Interactive split viewer showing bijective token replacements"
                    />
                    <div className="p-5">
                      <SplitCompare
                        original={result.preview.original}
                        sanitized={result.preview.sanitized}
                        columnMap={result.preview.column_map}
                        columnStrategies={result.preview.column_strategies}
                        originalTable={result.preview.table}
                        maskedTable={result.preview.masked_table}
                      />
                    </div>
                  </Panel>
                ) : null}
              </div>
            ) : null}

            {stage === 'export' && !result ? (
              <Panel>
                <EmptyState icon={<Vault size={20} />} title="No artifact sealed">
                  Execute a transformation to emit the masked artifact and its
                  encrypted .ciphermap vault.
                </EmptyState>
              </Panel>
            ) : null}

            {/* ============================ RESTORE =========================== */}
            {stage === 'restore' ? (
              <div className="grid gap-6 xl:grid-cols-[380px_minmax(0,1fr)]">
                <Panel>
                  <PanelHeader
                    icon={<RotateCcw size={15} />}
                    title="5 · Lossless de-anonymization"
                    subtitle="Supply sanitized artifact, vault and passphrase"
                  />
                  <div className="space-y-4 p-5">
                    <DropZone
                      file={rFile}
                      onFile={setRFile}
                      accept={ACCEPT_DATA}
                      label="Sanitized artifact"
                      hint="Masked dataset or downstream analytical output"
                      compact
                    />
                    <DropZone
                      file={rMap}
                      onFile={setRMap}
                      accept={ACCEPT_MAP}
                      label=".ciphermap vault"
                      hint="AES-256-GCM sealed mapping"
                      tone="vault"
                      compact
                    />
                    <PassphraseField
                      value={rPassphrase}
                      onChange={setRPassphrase}
                      label="Vault passphrase"
                      showStrength={false}
                      autoComplete="current-password"
                      hint="Must match the passphrase used when the vault was sealed"
                    />
                    <Button
                      tone="primary"
                      icon={<RotateCcw size={14} />}
                      disabled={!rFile || !rMap || rPassphrase.length < 8}
                      busy={busy !== null}
                      onClick={() => void runRestore()}
                      className="w-full"
                    >
                      Re-identify
                    </Button>
                  </div>
                </Panel>

                <div className="space-y-5">
                  {rResult ? (
                    <>
                      <Panel className="border-signal-500/30 bg-signal-500/5">
                        <div className="flex flex-wrap items-center justify-between gap-4 p-5">
                          <div className="flex items-center gap-3.5">
                            <span className="flex size-9 items-center justify-center rounded-lg border border-signal-500/30 bg-signal-500/10 text-signal-400">
                              <CheckCircle2 size={18} />
                            </span>
                            <div>
                              <div className="text-sm font-medium text-signal-400">
                                Re-identification verified
                              </div>
                              <p className="mt-0.5 text-xs text-slate-400">
                                {formatInt(rResult.statistics.values_restored)} values and{' '}
                                {formatInt(rResult.statistics.columns_restored)} columns
                                reversed across {formatInt(rResult.statistics.tables)}{' '}
                                table(s)
                              </p>
                            </div>
                          </div>
                          <Button
                            tone="primary"
                            icon={<Download size={14} />}
                            onClick={() => downloadArtifact(rResult.artifact)}
                          >
                            Download original
                          </Button>
                        </div>
                      </Panel>

                      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
                        <Stat
                          label="Rows restored"
                          value={formatInt(rResult.statistics.total_rows)}
                        />
                        <Stat
                          label="Columns restored"
                          value={formatInt(rResult.statistics.columns_restored)}
                        />
                        <Stat
                          label="Values restored"
                          value={formatInt(rResult.statistics.values_restored)}
                        />
                        <Stat
                          label="Output size"
                          value={formatBytes(rResult.artifact.size_bytes)}
                          hint={rResult.artifact.filename}
                        />
                      </div>

                      {rResult.preview ? (
                        <Panel>
                          <PanelHeader
                            icon={<Table2 size={15} />}
                            title="Restored dataset preview"
                            subtitle={`Table “${rResult.preview.table}” — original headers and values recovered`}
                          />
                          <div className="h-[420px]">
                            <DataGrid
                              frame={rResult.preview.restored}
                              tone="classified"
                              pageSize={12}
                            />
                          </div>
                        </Panel>
                      ) : null}
                    </>
                  ) : (
                    <Panel>
                      <EmptyState icon={<RotateCcw size={20} />} title="Awaiting inputs">
                        Unseals the AES-256-GCM vault with your Argon2id key and
                        inverts every bijection to reproduce the source relation bit-for-bit.
                      </EmptyState>
                    </Panel>
                  )}
                </div>
              </div>
            ) : null}

            {/* ============================= AUDIT ============================ */}
            {stage === 'audit' ? (
              <Panel>
                <PanelHeader
                  icon={<ScanLine size={15} />}
                  title="6 · Independent isomorphism audit"
                  subtitle="Recomputes aggregates directly from raw files without engine bias"
                  actions={
                    result && file ? (
                      <Button
                        tone="ghost"
                        icon={<FileDown size={13} />}
                        onClick={() => {
                          setAuditOriginal(file);
                          setAuditSanitized(
                            new File(
                              [
                                Uint8Array.from(atob(result.artifact.base64), (c) =>
                                  c.charCodeAt(0),
                                ),
                              ],
                              result.artifact.filename,
                              { type: result.artifact.mime_type },
                            ),
                          );
                          setAuditMap(
                            manifestToFile(
                              result.ciphermap.manifest,
                              result.ciphermap.filename,
                            ),
                          );
                          setAuditPassphrase(passphrase);
                          toasts.info(
                            'Session inputs loaded',
                            'Original, artifact and vault loaded from current workspace',
                          );
                        }}
                      >
                        Load current session
                      </Button>
                    ) : undefined
                  }
                />
                <div className="p-5">
                  <AuditPanel
                    originalFile={auditOriginal}
                    sanitizedFile={auditSanitized}
                    ciphermapFile={auditMap}
                    onOriginal={setAuditOriginal}
                    onSanitized={setAuditSanitized}
                    onCiphermap={setAuditMap}
                    passphrase={auditPassphrase}
                    onPassphrase={setAuditPassphrase}
                    result={auditResult}
                    busy={busy !== null}
                    onRun={() => void runAudit()}
                  />
                </div>
              </Panel>
            ) : null}
          </m.div>
        </AnimatePresence>
      </main>

      {/* ---------------------------------------------------------------- */}
      {/*  Footer                                                           */}
      {/* ---------------------------------------------------------------- */}
      <footer className="mx-auto max-w-[1600px] px-6 pt-2 pb-8">
        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-white/8 pt-4 text-xs text-slate-500">
          <span>
            AetherMask · CipherShift — local processing only. Zero external egress.
          </span>
          <span className="tabular flex items-center gap-3">
            <span>UI v{__AETHERMASK_UI_VERSION__}</span>
            {attestation ? <span>Engine v{attestation.version}</span> : null}
            <span>{formatInt(egress.total)} same-origin requests</span>
          </span>
        </div>
      </footer>

      <AttestationDrawer
        open={showAttestation}
        onClose={() => setShowAttestation(false)}
        attestation={attestation}
        clientEgress={egress}
      />

      <CommandPalette
        open={paletteOpen}
        onClose={() => setPaletteOpen(false)}
        commands={commands}
      />
    </div>
  );
}
