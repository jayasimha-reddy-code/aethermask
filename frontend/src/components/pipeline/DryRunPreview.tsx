/**
 * AetherMask (CipherShift) :: dry-run preview
 *
 * Surfaces `POST /api/v1/preview`: a transformation rehearsal that produces
 * no vault and no downloadable artifact.
 */

import { m } from 'motion/react';
import { Eye, Loader2, Play, ShieldQuestion } from 'lucide-react';
import type { PreviewResponse } from '../../lib/api';
import { formatInt } from '../../lib/format';
import { useVerdictVariants } from '../../hooks/useReducedMotionVariants';
import { Badge, Button, EmptyState } from '../ui/Primitives';
import { SplitCompare } from '../grid/SplitCompare';
import { ParityCharts } from './ParityCharts';

export function DryRunPreview({
  preview,
  busy,
  onRun,
  canRun,
  profileTitle,
}: {
  preview: PreviewResponse | null;
  busy: boolean;
  onRun: () => void;
  canRun: boolean;
  profileTitle: string;
}) {
  const verdictVariants = useVerdictVariants();

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-white/8 bg-abyss-850/60 p-4">
        <div className="flex items-start gap-3">
          <Eye size={16} className="mt-0.5 shrink-0 text-slate-400" aria-hidden="true" />
          <div>
            <h3 className="text-xs font-medium text-slate-200">
              Rehearse the projection
            </h3>
            <p className="mt-0.5 text-xs leading-relaxed text-slate-400">
              Runs the full transformation in local memory and verifies analytical parity
              without sealing a vault or emitting an artifact.
            </p>
          </div>
        </div>
        <Button
          tone="neutral"
          icon={busy ? <Loader2 size={13} className="animate-spin" /> : <Play size={13} />}
          disabled={!canRun}
          busy={busy}
          onClick={onRun}
        >
          {preview ? 'Re-run dry run' : 'Run dry run'}
        </Button>
      </div>

      {preview ? (
        <>
          <m.div
            variants={verdictVariants}
            initial="hidden"
            animate="visible"
            className={`flex flex-wrap items-center justify-between gap-3 rounded-xl border p-4 ${
              preview.fidelity.passed
                ? 'border-signal-500/30 bg-signal-500/5'
                : 'border-caution-500/30 bg-caution-500/5'
            }`}
          >
            <div>
              <div
                className={`text-xs font-medium ${
                  preview.fidelity.passed ? 'text-signal-400' : 'text-caution-400'
                }`}
              >
                {preview.fidelity.passed
                  ? 'Dry run verified: isomorphism holds'
                  : 'Dry run identified drift'}
              </div>
              <p className="mt-0.5 text-xs text-slate-400">
                {formatInt(preview.fidelity.passed_checks)} of{' '}
                {formatInt(preview.fidelity.total_checks)} invariants verified ·{' '}
                {preview.profile_title || profileTitle}
              </p>
            </div>
            <Badge tone="muted">No vault written</Badge>
          </m.div>

          {preview.chart ? <ParityCharts chart={preview.chart} /> : null}

          <SplitCompare
            original={preview.original}
            sanitized={preview.sanitized}
            columnMap={preview.column_map}
            columnStrategies={preview.column_strategies}
            originalTable={preview.table}
            maskedTable={preview.column_map[preview.table] ?? preview.table}
          />
        </>
      ) : (
        <EmptyState icon={<ShieldQuestion size={18} />} title="No dry run yet">
          Audition the selected cover domain before committing a passphrase.
          The rehearsal state clears once navigated away.
        </EmptyState>
      )}
    </div>
  );
}
