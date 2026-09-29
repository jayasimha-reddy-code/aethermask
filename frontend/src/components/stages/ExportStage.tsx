import {
  Activity,
  CheckCircle2,
  Download,
  Fingerprint,
  Lock,
  RotateCcw,
  Table2,
  Vault,
} from 'lucide-react';
import type { ArtifactInfo, ObfuscateResponse } from '../../lib/types';
import { formatBytes, formatInt, shortHash } from '../../lib/format';
import { Badge, Button, Copyable, EmptyState, Panel, PanelHeader, Stat } from '../ui/Primitives';
import { ParityCharts } from '../pipeline/ParityCharts';
import { SplitCompare } from '../grid/SplitCompare';

export interface ExportStageProps {
  result: ObfuscateResponse | null;
  downloadArtifact: (a: ArtifactInfo) => void;
  downloadManifest: (manifest: Record<string, unknown>, filename: string) => void;
  handoffToRestore: () => void;
}

export function ExportStage({
  result,
  downloadArtifact,
  downloadManifest,
  handoffToRestore,
}: ExportStageProps) {
  if (!result) {
    return (
      <Panel>
        <EmptyState icon={<Vault size={20} />} title="No artifact sealed">
          Execute a transformation to emit the masked artifact and its
          encrypted .ciphermap vault.
        </EmptyState>
      </Panel>
    );
  }

  return (
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
  );
}
