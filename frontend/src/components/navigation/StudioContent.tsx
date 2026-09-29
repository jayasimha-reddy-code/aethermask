import { AnimatePresence, m } from 'motion/react';
import type { Variants } from 'motion/react';
import { downloadArtifact, downloadManifest } from '../../lib/api';
import type { StudioState } from '../../hooks/useStudioState';
import type { StudioOperations } from '../../hooks/useStudioOperations';
import { IngestStage } from '../stages/IngestStage';
import { ProfileStage } from '../stages/ProfileStage';
import { TransformStage } from '../stages/TransformStage';
import { ExportStage } from '../stages/ExportStage';
import { RestoreStage } from '../stages/RestoreStage';
import { AuditStage } from '../stages/AuditStage';

export interface StudioContentProps {
  state: StudioState;
  operations: StudioOperations;
  stageVariants: Variants;
  acceptData: string;
  acceptMap: string;
}

export function StudioContent({
  state,
  operations,
  stageVariants,
  acceptData,
  acceptMap,
}: StudioContentProps) {
  const {
    stage,
    direction,
    go,
    busy,
    file,
    setFile,
    datasetName,
    setDatasetName,
    profile,
    setProfile,
    profiles,
    attestation,
    selectedProfile,
    setSelectedProfile,
    numericMode,
    setNumericMode,
    passphrase,
    setPassphrase,
    seed,
    setSeed,
    result,
    setResult,
    rFile,
    setRFile,
    rMap,
    setRMap,
    rPassphrase,
    setRPassphrase,
    rResult,
    dryRun,
    showDryRun,
    setShowDryRun,
    auditOriginal,
    setAuditOriginal,
    auditSanitized,
    setAuditSanitized,
    auditMap,
    setAuditMap,
    auditPassphrase,
    setAuditPassphrase,
    auditResult,
    toasts,
  } = state;

  const {
    runProfile,
    runObfuscate,
    runRestore,
    runDryRun,
    runAudit,
    handoffToRestore,
  } = operations;

  return (
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
          {stage === 'ingest' ? (
            <IngestStage
              file={file}
              setFile={setFile}
              setProfile={setProfile}
              setResult={setResult}
              datasetName={datasetName}
              setDatasetName={setDatasetName}
              busy={busy}
              runProfile={runProfile}
              go={go}
              attestation={attestation}
              acceptData={acceptData}
            />
          ) : null}

          {stage === 'profile' ? (
            <ProfileStage profile={profile} go={go} />
          ) : null}

          {stage === 'transform' ? (
            <TransformStage
              config={{
                profiles,
                selectedProfile,
                setSelectedProfile,
                profile,
                numericMode,
                setNumericMode,
                passphrase,
                setPassphrase,
                seed,
                setSeed,
              }}
              dryRun={{
                showDryRun,
                setShowDryRun,
                dryRun,
                runDryRun,
              }}
              file={file}
              busy={busy}
              runObfuscate={runObfuscate}
              go={go}
            />
          ) : null}

          {stage === 'export' ? (
            <ExportStage
              result={result}
              downloadArtifact={downloadArtifact}
              downloadManifest={downloadManifest}
              handoffToRestore={handoffToRestore}
            />
          ) : null}

          {stage === 'restore' ? (
            <RestoreStage
              rFile={rFile}
              setRFile={setRFile}
              rMap={rMap}
              setRMap={setRMap}
              rPassphrase={rPassphrase}
              setRPassphrase={setRPassphrase}
              busy={busy}
              runRestore={runRestore}
              rResult={rResult}
              downloadArtifact={downloadArtifact}
              acceptData={acceptData}
              acceptMap={acceptMap}
            />
          ) : null}

          {stage === 'audit' ? (
            <AuditStage
              files={{
                original: auditOriginal,
                setOriginal: setAuditOriginal,
                sanitized: auditSanitized,
                setSanitized: setAuditSanitized,
                map: auditMap,
                setMap: setAuditMap,
                passphrase: auditPassphrase,
                setPassphrase: setAuditPassphrase,
              }}
              session={{
                result,
                file,
                passphrase,
              }}
              auditResult={auditResult}
              busy={busy}
              runAudit={runAudit}
              showNotice={(title, desc) => toasts.info(title, desc)}
            />
          ) : null}
        </m.div>
      </AnimatePresence>
    </main>
  );
}
