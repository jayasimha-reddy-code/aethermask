/**
 * AetherMask (CipherShift) :: independent isomorphism audit
 *
 * Surfaces `POST /api/v1/verify`, which takes the (original, sanitized,
 * ciphermap) triple and recomputes aggregates on both sides from scratch.
 */

import { useMemo, useState } from 'react';
import { AnimatePresence, m } from 'motion/react';
import { CheckCircle2, ScanLine, ShieldAlert, XCircle } from 'lucide-react';
import type { VerifyResponse } from '../../lib/api';
import { formatInt, shortHash } from '../../lib/format';
import {
  useListVariants,
  useVerdictVariants,
} from '../../hooks/useReducedMotionVariants';
import { Badge, Button, Copyable, EmptyState, MeterBar } from '../ui/Primitives';
import { DropZone, PassphraseField } from '../pipeline/Controls';
import { SearchInput } from '../grid/DataGrid';

export function AuditPanel({
  originalFile,
  sanitizedFile,
  ciphermapFile,
  onOriginal,
  onSanitized,
  onCiphermap,
  passphrase,
  onPassphrase,
  result,
  busy,
  onRun,
}: {
  originalFile: File | null;
  sanitizedFile: File | null;
  ciphermapFile: File | null;
  onOriginal: (f: File | null) => void;
  onSanitized: (f: File | null) => void;
  onCiphermap: (f: File | null) => void;
  passphrase: string;
  onPassphrase: (v: string) => void;
  result: VerifyResponse | null;
  busy: boolean;
  onRun: () => void;
}) {
  const [query, setQuery] = useState('');
  const [onlyFailed, setOnlyFailed] = useState(false);
  const verdictVariants = useVerdictVariants();
  const { container, item } = useListVariants();

  const ready =
    !!originalFile && !!sanitizedFile && !!ciphermapFile && passphrase.length >= 8;

  const checks = useMemo(() => {
    if (!result) return [];
    const q = query.trim().toLowerCase();
    return result.checks.filter((c) => {
      if (onlyFailed && c.ok) return false;
      if (!q) return true;
      return (
        c.check.toLowerCase().includes(q) || c.detail.toLowerCase().includes(q)
      );
    });
  }, [result, query, onlyFailed]);

  const passedCount = result ? result.total_checks - result.failed_checks : 0;

  return (
    <div className="grid gap-5 xl:grid-cols-[380px_minmax(0,1fr)]">
      <div className="space-y-4">
        <div className="rounded-xl border border-white/8 bg-abyss-850/60 p-4">
          <h3 className="flex items-center gap-2 text-xs font-medium text-slate-200">
            <ScanLine size={14} className="text-signal-400" aria-hidden="true" />
            Independent verification
          </h3>
          <p className="mt-1 text-xs leading-relaxed text-slate-400">
            Recomputes row counts, cardinality, null topologies and numeric sums
            directly from the three files: independently of the engine that produced them.
          </p>
        </div>

        <DropZone
          file={originalFile}
          onFile={onOriginal}
          accept=".csv,.tsv,.parquet,.xlsx,.xls,.json,.sql,.txt"
          label="Confidential original"
          hint="Pre-masking source dataset"
          compact
        />
        <DropZone
          file={sanitizedFile}
          onFile={onSanitized}
          accept=".csv,.tsv,.parquet,.xlsx,.xls,.json,.sql,.txt"
          label="Sanitized artifact"
          hint="Masked output dataset"
          compact
        />
        <DropZone
          file={ciphermapFile}
          onFile={onCiphermap}
          accept=".ciphermap,.json"
          label=".ciphermap vault"
          hint="AES-256-GCM encrypted mapping"
          tone="vault"
          compact
        />
        <PassphraseField
          value={passphrase}
          onChange={onPassphrase}
          label="Vault passphrase"
          showStrength={false}
          autoComplete="current-password"
          hint="Required to decrypt and verify the bijective mapping"
        />
        <Button
          tone="primary"
          icon={<ScanLine size={14} />}
          disabled={!ready}
          busy={busy}
          onClick={onRun}
          className="w-full"
        >
          Run independent audit
        </Button>
      </div>

      <div className="space-y-4">
        <AnimatePresence mode="wait" initial={false}>
          {result ? (
            <m.div
              key="result"
              variants={verdictVariants}
              initial="hidden"
              animate="visible"
              className="space-y-4"
            >
              <div
                className={`rounded-xl border p-4 ${
                  result.passed
                    ? 'border-signal-500/30 bg-signal-500/5'
                    : 'border-classified-500/30 bg-classified-500/5'
                }`}
              >
                <div className="flex flex-wrap items-center justify-between gap-4">
                  <div className="flex items-center gap-3">
                    {result.passed ? (
                      <CheckCircle2 size={22} className="text-signal-400" aria-hidden="true" />
                    ) : (
                      <ShieldAlert size={22} className="text-classified-400" aria-hidden="true" />
                    )}
                    <div>
                      <div
                        className={`text-sm font-medium ${
                          result.passed ? 'text-signal-400' : 'text-classified-400'
                        }`}
                      >
                        {result.passed
                          ? 'Audit verified: artifact is an isomorphic image'
                          : `Audit failed: ${formatInt(result.failed_checks)} discrepancy(ies)`}
                      </div>
                      <p className="mt-0.5 text-xs text-slate-400">
                        {formatInt(passedCount)} of {formatInt(result.total_checks)}{' '}
                        recomputed invariants hold
                      </p>
                    </div>
                  </div>
                  {result.schema_fingerprint ? (
                    <Copyable
                      value={result.schema_fingerprint}
                      display={`Schema ${shortHash(result.schema_fingerprint, 10, 4)}`}
                    />
                  ) : null}
                </div>
                <MeterBar
                  value={passedCount}
                  max={result.total_checks}
                  tone={result.passed ? 'signal' : 'classified'}
                  className="mt-3"
                  label="Audit checks passed"
                />
              </div>

              <div className="overflow-hidden rounded-xl border border-white/8 bg-abyss-850/40">
                <div className="flex flex-wrap items-center gap-3 border-b border-white/8 bg-abyss-850/80 px-4 py-3">
                  <div className="min-w-[200px] flex-1">
                    <SearchInput
                      value={query}
                      onChange={setQuery}
                      placeholder="Filter checks…"
                      label="Filter audit checks"
                    />
                  </div>
                  <label className="flex shrink-0 cursor-pointer items-center gap-2 text-xs text-slate-400 select-none">
                    <input
                      type="checkbox"
                      checked={onlyFailed}
                      onChange={(e) => setOnlyFailed(e.target.checked)}
                      className="size-3.5 rounded border-white/12 bg-abyss-900 text-signal-500"
                    />
                    Only failures
                  </label>
                  <Badge tone={result.passed ? 'signal' : 'classified'}>
                    {formatInt(checks.length)} shown
                  </Badge>
                </div>

                <m.ul
                  className="max-h-[420px] overflow-auto"
                  variants={container}
                  initial="hidden"
                  animate="visible"
                >
                  {checks.map((c, i) => (
                    <m.li
                      key={`${c.check}-${i}`}
                      variants={item}
                      className="flex items-center gap-3 border-t border-white/4 px-4 py-2 first:border-t-0 hover:bg-abyss-800/40 transition-colors"
                    >
                      {c.ok ? (
                        <CheckCircle2 size={13} className="shrink-0 text-signal-400" aria-hidden="true" />
                      ) : (
                        <XCircle size={13} className="shrink-0 text-classified-400" aria-hidden="true" />
                      )}
                      <span className="tabular min-w-0 flex-1 truncate text-xs text-slate-200">
                        {c.check}
                      </span>
                      <span
                        className={`tabular shrink-0 text-xs ${
                          c.ok ? 'text-slate-500' : 'text-classified-400 font-medium'
                        }`}
                      >
                        {c.detail}
                      </span>
                    </m.li>
                  ))}
                </m.ul>
              </div>
            </m.div>
          ) : (
            <div className="rounded-xl border border-white/8 bg-abyss-850/40">
              <EmptyState icon={<ScanLine size={18} />} title="No audit run yet">
                Provide the original, sanitized artifact and vault. Recomputes
                every statistical aggregate from the raw files independently.
              </EmptyState>
            </div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
