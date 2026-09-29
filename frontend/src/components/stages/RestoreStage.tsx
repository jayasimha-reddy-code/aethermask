import { CheckCircle2, Download, RotateCcw, Table2 } from 'lucide-react';
import type { ArtifactInfo, RestoreResponse } from '../../lib/types';
import { formatBytes, formatInt } from '../../lib/format';
import { Button, EmptyState, Panel, PanelHeader, Stat } from '../ui/Primitives';
import { DropZone, PassphraseField } from '../pipeline/Controls';
import { DataGrid } from '../grid/DataGrid';

export interface RestoreStageProps {
  rFile: File | null;
  setRFile: (f: File | null) => void;
  rMap: File | null;
  setRMap: (f: File | null) => void;
  rPassphrase: string;
  setRPassphrase: (p: string) => void;
  busy: string | null;
  runRestore: () => Promise<void>;
  rResult: RestoreResponse | null;
  downloadArtifact: (a: ArtifactInfo) => void;
  acceptData: string;
  acceptMap: string;
}

export function RestoreStage({
  rFile,
  setRFile,
  rMap,
  setRMap,
  rPassphrase,
  setRPassphrase,
  busy,
  runRestore,
  rResult,
  downloadArtifact,
  acceptData,
  acceptMap,
}: RestoreStageProps) {
  return (
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
            accept={acceptData}
            label="Sanitized artifact"
            hint="Masked dataset or downstream analytical output"
            compact
          />
          <DropZone
            file={rMap}
            onFile={setRMap}
            accept={acceptMap}
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
                  subtitle={`Table "${rResult.preview.table}" (original headers and values recovered)`}
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
  );
}
