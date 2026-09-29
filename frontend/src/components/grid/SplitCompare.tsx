/**
 * AetherMask (CipherShift) :: SplitCompare
 *
 * Side-by-side confidential / sanitized view with a draggable divider, plus a
 * column-mapping ledger showing which transformation strategy was applied to
 * each field.
 */

import { useCallback, useMemo, useRef, useState } from 'react';
import { m } from 'motion/react';
import { ArrowRight, EyeOff, GripVertical, Shield, ShieldCheck } from 'lucide-react';
import type { FramePreview } from '../../lib/types';
import { DataGrid } from './DataGrid';
import { Badge } from '../ui/Primitives';
import { listItemVariants, listVariants } from '../../lib/motion';

const STRATEGY_LABEL: Record<string, string> = {
  identity: 'Untouched',
  preserved: 'Preserved',
  empty: 'Empty',
  passthrough: 'Passthrough',
  affine: 'Affine y=ax+b',
  numeric_identifier_bijection: 'Numeric key bijection',
  identifier_bijection: 'Identifier bijection',
  categorical_bijection: 'Categorical bijection',
  free_text_ner: 'Free-text NER',
};

const STRATEGY_TONE: Record<
  string,
  'signal' | 'vault' | 'caution' | 'muted' | 'neutral'
> = {
  identity: 'muted',
  preserved: 'muted',
  empty: 'muted',
  passthrough: 'muted',
  affine: 'caution',
  numeric_identifier_bijection: 'vault',
  identifier_bijection: 'vault',
  categorical_bijection: 'signal',
  free_text_ner: 'signal',
};

export interface SplitCompareProps {
  original: FramePreview;
  sanitized: FramePreview;
  columnMap: Record<string, string>;
  columnStrategies: Record<string, string>;
  originalTable: string;
  maskedTable: string;
}

export function SplitCompare({
  original,
  sanitized,
  columnMap,
  columnStrategies,
  originalTable,
  maskedTable,
}: SplitCompareProps) {
  const [split, setSplit] = useState(50);
  const containerRef = useRef<HTMLDivElement>(null);

  // Columns whose values actually changed get highlighted in both grids.
  const { hotOriginal, hotMasked } = useMemo(() => {
    const ho = new Set<string>();
    const hm = new Set<string>();
    for (const [src, strategy] of Object.entries(columnStrategies)) {
      const inert =
        strategy === 'identity' ||
        strategy === 'preserved' ||
        strategy === 'passthrough' ||
        strategy === 'empty';
      if (!inert) {
        ho.add(src);
        const dst = columnMap[src];
        if (dst) hm.add(dst);
      }
    }
    return { hotOriginal: ho, hotMasked: hm };
  }, [columnMap, columnStrategies]);

  const renamedCount = useMemo(
    () => Object.entries(columnMap).filter(([a, b]) => a !== b).length,
    [columnMap],
  );

  const onDrag = useCallback((clientX: number) => {
    const el = containerRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const pct = ((clientX - rect.left) / rect.width) * 100;
    setSplit(Math.max(18, Math.min(82, pct)));
  }, []);

  return (
    <div className="space-y-4">
      {/* Split grids */}
      <div
        ref={containerRef}
        className="relative flex h-[440px] overflow-hidden rounded-xl border border-white/8 bg-abyss-900/60"
      >
        {/* Confidential side */}
        <div
          className="hatch-classified flex min-w-0 flex-col"
          style={{ width: `${split}%` }}
        >
          <div className="flex items-center justify-between gap-2 border-b border-white/8 bg-abyss-850/90 px-3 py-2">
            <div className="flex min-w-0 items-center gap-2">
              <Shield size={14} className="shrink-0 text-classified-400" aria-hidden="true" />
              <span className="truncate text-xs font-medium text-slate-200">
                Confidential source
              </span>
            </div>
            <span className="tabular shrink-0 truncate text-xs text-slate-500">
              {originalTable}
            </span>
          </div>
          <div className="min-h-0 flex-1">
            <DataGrid
              frame={original}
              tone="classified"
              highlight={hotOriginal}
              pageSize={10}
              emptyLabel="No source rows"
            />
          </div>
        </div>

        {/* Divider */}
        <div className="relative z-20 w-px shrink-0 bg-white/12">
          <div className="absolute inset-y-0 -left-3 w-6">
            <input
              type="range"
              min={18}
              max={82}
              step={1}
              value={split}
              onChange={(e) => setSplit(Number(e.target.value))}
              onMouseDown={(e) => {
                const move = (ev: MouseEvent) => onDrag(ev.clientX);
                const up = () => {
                  window.removeEventListener('mousemove', move);
                  window.removeEventListener('mouseup', up);
                };
                window.addEventListener('mousemove', move);
                window.addEventListener('mouseup', up);
                e.preventDefault();
              }}
              aria-label="Adjust comparison split position"
              className="h-full w-full cursor-col-resize opacity-0"
            />
            <div className="pointer-events-none absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 rounded-md border border-white/12 bg-abyss-800 p-1 text-slate-400 shadow-md">
              <GripVertical size={13} aria-hidden="true" />
            </div>
          </div>
        </div>

        {/* Sanitized side */}
        <div className="hatch-signal flex min-w-0 flex-1 flex-col">
          <div className="flex items-center justify-between gap-2 border-b border-white/8 bg-abyss-850/90 px-3 py-2">
            <div className="flex min-w-0 items-center gap-2">
              <ShieldCheck size={14} className="shrink-0 text-signal-400" aria-hidden="true" />
              <span className="truncate text-xs font-medium text-slate-200">
                Sanitized cover
              </span>
            </div>
            <span className="tabular shrink-0 truncate text-xs text-slate-500">
              {maskedTable}
            </span>
          </div>
          <div className="min-h-0 flex-1">
            <DataGrid
              frame={sanitized}
              tone="signal"
              highlight={hotMasked}
              pageSize={10}
              emptyLabel="No sanitized rows"
            />
          </div>
        </div>
      </div>

      {/* Column mapping ledger */}
      <div className="overflow-hidden rounded-xl border border-white/8">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/8 bg-abyss-850/80 px-4 py-3">
          <h3 className="text-xs font-medium text-slate-200">
            Column transformation ledger
          </h3>
          <div className="flex gap-2">
            <Badge tone="muted">{Object.keys(columnMap).length} columns</Badge>
            <Badge tone="signal">{renamedCount} renamed</Badge>
            <Badge tone="muted">{hotOriginal.size} value-substituted</Badge>
          </div>
        </div>
        <div className="max-h-64 overflow-auto">
          <m.table
            className="w-full text-left text-xs"
            variants={listVariants}
            initial="hidden"
            animate="visible"
          >
            <thead className="sticky top-0 bg-abyss-850/95 backdrop-blur">
              <tr className="text-slate-400 border-b border-white/6">
                <th scope="col" className="px-4 py-2 font-medium">
                  Source field
                </th>
                <th scope="col" className="w-8" />
                <th scope="col" className="px-2 py-2 font-medium">
                  Cover field
                </th>
                <th scope="col" className="px-4 py-2 font-medium">
                  Strategy
                </th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(columnMap).map(([src, dst]) => {
                const strategy = columnStrategies[src] ?? 'identity';
                return (
                  <m.tr
                    key={src}
                    variants={listItemVariants}
                    className="border-t border-white/4 hover:bg-abyss-800/40 transition-colors"
                  >
                    <td className="tabular px-4 py-2 text-classified-400">{src}</td>
                    <td className="py-2 text-center text-slate-600">
                      <ArrowRight size={12} className="inline" aria-hidden="true" />
                    </td>
                    <td className="tabular px-2 py-2 text-signal-400">
                      {dst}
                      {src === dst ? (
                        <span className="ml-1.5 text-xs text-slate-500">
                          (unchanged)
                        </span>
                      ) : null}
                    </td>
                    <td className="px-4 py-2">
                      <Badge tone={STRATEGY_TONE[strategy] ?? 'neutral'}>
                        {(STRATEGY_TONE[strategy] ?? 'neutral') === 'muted' ? (
                          <EyeOff size={11} aria-hidden="true" />
                        ) : null}
                        {STRATEGY_LABEL[strategy] ?? strategy}
                      </Badge>
                    </td>
                  </m.tr>
                );
              })}
            </tbody>
          </m.table>
        </div>
      </div>
    </div>
  );
}
