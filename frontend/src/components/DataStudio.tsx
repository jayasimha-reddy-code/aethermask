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

import {
  useRevealVariants,
  useStageVariants,
} from '../hooks/useReducedMotionVariants';
import { useStudioState } from '../hooks/useStudioState';
import { useStudioCommands } from '../hooks/useStudioCommands';
import { useStudioOperations } from '../hooks/useStudioOperations';

import { AttestationDrawer } from './audit/Attestation';
import { CommandPalette, useCommandPaletteHotkey } from './navigation/CommandPalette';
import { StudioHeader } from './navigation/StudioHeader';
import { StudioFooter } from './navigation/StudioFooter';
import { StatusStrip } from './navigation/StatusStrip';
import { StudioContent } from './navigation/StudioContent';

const ACCEPT_DATA = '.csv,.tsv,.parquet,.xlsx,.xls,.json,.sql,.txt';
const ACCEPT_MAP = '.ciphermap,.json';

/* ========================================================================== */
/*  Main component                                                             */
/* ========================================================================== */

export default function DataStudio() {
  const state = useStudioState();
  const operations = useStudioOperations(state);
  const commands = useStudioCommands(state, operations);
  useCommandPaletteHotkey(() => state.setPaletteOpen(true));

  const stageVariants = useStageVariants();
  const revealVariants = useRevealVariants();

  return (
    <div className="min-h-screen bg-abyss-950 text-slate-100">
      <StudioHeader
        setPaletteOpen={state.setPaletteOpen}
        setShowAttestation={state.setShowAttestation}
        egress={state.egress}
        resetAll={operations.resetAll}
        stage={state.stage}
        onJump={state.go}
        reachable={state.reachable}
      />

      <StatusStrip
        busy={state.busy}
        error={state.error}
        notice={state.notice}
        revealVariants={revealVariants}
        onDismissError={() => state.setError(null)}
        onDismissNotice={() => state.setNotice(null)}
      />

      <StudioContent
        state={state}
        operations={operations}
        stageVariants={stageVariants}
        acceptData={ACCEPT_DATA}
        acceptMap={ACCEPT_MAP}
      />

      <StudioFooter />

      <AttestationDrawer
        open={state.showAttestation}
        onClose={() => state.setShowAttestation(false)}
        attestation={state.attestation}
        clientEgress={state.egress}
      />

      <CommandPalette
        open={state.paletteOpen}
        onClose={() => state.setPaletteOpen(false)}
        commands={commands}
      />
    </div>
  );
}
