import {
  Download,
  Lock,
  Play,
  RefreshCw,
  RotateCcw,
  ScanLine,
  ScanSearch,
  ShieldCheck,
  Vault,
} from 'lucide-react';
import { downloadArtifact, downloadManifest } from '../lib/api';
import type { ObfuscateResponse, Stage } from '../lib/types';
import type { Command } from '../components/navigation/CommandPalette';
import { STAGES } from '../components/navigation/StageRail';
import type { StudioState } from './useStudioState';
import type { StudioOperations } from './useStudioOperations';

function buildNavCommands(reachable: Set<Stage>, go: (s: Stage) => void): Command[] {
  return STAGES.map(({ id, label, Icon, blurb }) => ({
    id: `go-${id}`,
    group: 'Navigate',
    label: `Go to ${label}`,
    hint: blurb,
    icon: <Icon size={13} />,
    disabled: !reachable.has(id),
    keywords: `${id} stage ${blurb}`,
    run() {
      go(id);
    },
  }));
}

function buildActionCommands(
  state: StudioState,
  operations: StudioOperations,
): Command[] {
  const {
    file,
    busy,
    passphrase,
    rFile,
    rMap,
    rPassphrase,
    auditOriginal,
    auditSanitized,
    auditMap,
    auditPassphrase,
  } = state;

  return [
    {
      id: 'act-profile',
      group: 'Actions',
      label: 'Analyse sensitivity',
      hint: 'Offline risk grading of the loaded dataset',
      icon: <ScanSearch size={13} />,
      disabled: !file || busy !== null,
      keywords: 'profile scan risk grade sensitivity',
      run() {
        void operations.runProfile();
      },
    },
    {
      id: 'act-dryrun',
      group: 'Actions',
      label: 'Run dry run (no vault)',
      hint: 'Audition the projection without sealing anything',
      icon: <Play size={13} />,
      disabled: !file || busy !== null,
      keywords: 'preview rehearse dry run audition',
      run() {
        state.go('transform');
        state.setShowDryRun(true);
        void operations.runDryRun();
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
      run() {
        void operations.runObfuscate();
      },
    },
    {
      id: 'act-restore',
      group: 'Actions',
      label: 'Re-identify dataset',
      hint: 'Reverse transformation losslessly',
      icon: <RotateCcw size={13} />,
      disabled: !rFile || !rMap || rPassphrase.length < 8 || busy !== null,
      keywords: 'restore reverse deanonymize re-identify',
      run() {
        state.go('restore');
        void operations.runRestore();
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
      run() {
        state.go('audit');
        void operations.runAudit();
      },
    },
  ];
}

function buildExportCommands(
  result: ObfuscateResponse | null,
  handoffToRestore: () => void,
): Command[] {
  if (!result) return [];
  return [
    {
      id: 'dl-artifact',
      group: 'Export',
      label: 'Download sanitized artifact',
      hint: result.artifact.filename,
      icon: <Download size={13} />,
      keywords: 'download export artifact csv output',
      run() {
        downloadArtifact(result.artifact);
      },
    },
    {
      id: 'dl-vault',
      group: 'Export',
      label: 'Download .ciphermap vault',
      hint: result.ciphermap.filename,
      icon: <Vault size={13} />,
      keywords: 'download vault ciphermap key mapping',
      run() {
        downloadManifest(
          result.ciphermap.manifest as Record<string, unknown>,
          result.ciphermap.filename,
        );
      },
    },
    {
      id: 'handoff',
      group: 'Export',
      label: 'Verify round-trip',
      hint: 'Load artifact and vault into restore stage',
      icon: <RotateCcw size={13} />,
      keywords: 'roundtrip handoff verify restore',
      run() {
        handoffToRestore();
      },
    },
  ];
}

function buildSystemCommands(
  externalCalls: number,
  setShowAttestation: (v: boolean) => void,
  resetAll: () => void,
): Command[] {
  return [
    {
      id: 'sys-attest',
      group: 'System',
      label: 'Open air-gap attestation',
      hint: `${externalCalls} external call(s) observed`,
      icon: <ShieldCheck size={13} />,
      keywords: 'attestation airgap offline egress network proof',
      run() {
        setShowAttestation(true);
      },
    },
    {
      id: 'sys-reset',
      group: 'System',
      label: 'Reset session',
      hint: 'Discard all in-memory buffers',
      icon: <RefreshCw size={13} />,
      keywords: 'reset clear wipe discard new',
      run() {
        resetAll();
      },
    },
  ];
}

export function buildStudioCommands(
  state: StudioState,
  operations: StudioOperations,
): Command[] {
  const nav = buildNavCommands(state.reachable, state.go);
  const actions = buildActionCommands(state, operations);
  const exports = buildExportCommands(state.result, operations.handoffToRestore);
  const system = buildSystemCommands(
    state.egress.external.length,
    state.setShowAttestation,
    operations.resetAll,
  );
  return [...nav, ...actions, ...exports, ...system];
}

export const useStudioCommands = buildStudioCommands;
