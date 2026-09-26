/**
 * AetherMask (CipherShift) :: ParityCharts
 *
 * The visual proof of the isomorphism guarantee. The confidential series and
 * the sanitized series are drawn on the SAME axes; if the transformation is
 * truly measure-preserving the two overlay exactly and Σ|Δ| is zero.
 */

import { useMemo, useState } from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { AnimatePresence, m } from 'motion/react';
import { BarChart3, LineChart as LineIcon, Sigma } from 'lucide-react';
import type { ChartBlock } from '../lib/types';
import { formatCompact, formatInt } from '../lib/format';
import { fadeVariants, verdictVariants } from '../lib/motion';

const COLOR_CLASSIFIED = '#f87171';
const COLOR_SIGNAL = '#2dd4bf';
const COLOR_GRID = '#1c2233';
const COLOR_AXIS = '#64748b';

interface MergedPoint {
  index: number;
  originalName: string;
  sanitizedName: string;
  confidential: number;
  sanitized: number;
  delta: number;
  countConfidential: number;
  countSanitized: number;
}

/** Custom tooltip: local component, no external theme package. */
function ParityTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: { payload?: MergedPoint }[];
}) {
  if (!active || !payload?.length) return null;
  const point = payload[0]?.payload;
  if (!point) return null;
  return (
    <div className="panel p-3 text-xs">
      <div className="mb-2 flex items-center gap-2 border-b border-white/8 pb-2">
        <span className="font-medium text-classified-400">
          {point.originalName}
        </span>
        <span className="text-slate-500">→</span>
        <span className="font-medium text-signal-400">
          {point.sanitizedName}
        </span>
      </div>
      <dl className="tabular space-y-1">
        <div className="flex justify-between gap-6">
          <dt className="text-classified-400">Confidential</dt>
          <dd className="text-slate-200">{formatInt(point.confidential)}</dd>
        </div>
        <div className="flex justify-between gap-6">
          <dt className="text-signal-400">Sanitized</dt>
          <dd className="text-slate-200">{formatInt(point.sanitized)}</dd>
        </div>
        <div className="mt-1 flex justify-between gap-6 border-t border-white/8 pt-1">
          <dt className="text-slate-400">|Δ|</dt>
          <dd
            className={
              point.delta === 0 ? 'text-signal-400 font-medium' : 'text-classified-400 font-medium'
            }
          >
            {point.delta === 0 ? '0 (exact)' : formatInt(point.delta)}
          </dd>
        </div>
        <div className="flex justify-between gap-6">
          <dt className="text-slate-500">Row count</dt>
          <dd className="text-slate-400">
            {formatInt(point.countConfidential)} / {formatInt(point.countSanitized)}
          </dd>
        </div>
      </dl>
    </div>
  );
}

export function ParityCharts({ chart }: { chart: ChartBlock }) {
  const [mode, setMode] = useState<'bars' | 'trend'>('bars');

  const { merged, totalDelta, maxDelta, exact } = useMemo(() => {
    const rows: MergedPoint[] = chart.original_series.map((orig, i) => {
      const san = chart.sanitized_series[i];
      const sanitizedValue = san?.value ?? 0;
      return {
        index: i,
        originalName: orig.name,
        sanitizedName: san?.name ?? '-',
        confidential: orig.value,
        sanitized: sanitizedValue,
        delta: Math.abs(orig.value - sanitizedValue),
        countConfidential: orig.count,
        countSanitized: san?.count ?? 0,
      };
    });
    const total = rows.reduce((acc, r) => acc + r.delta, 0);
    const max = rows.reduce((acc, r) => Math.max(acc, r.delta), 0);
    return {
      merged: rows,
      totalDelta: total,
      maxDelta: max,
      exact: total === 0,
    };
  }, [chart]);

  return (
    <div className="flex flex-col gap-4">
      {/* Verdict banner */}
      <m.div
        variants={verdictVariants}
        initial="hidden"
        animate="visible"
        className={`flex flex-wrap items-center justify-between gap-3 rounded-xl border p-4 ${
          exact
            ? 'border-signal-500/30 bg-signal-500/5'
            : 'border-caution-500/30 bg-caution-500/5'
        }`}
      >
        <div className="flex items-center gap-3">
          <Sigma
            size={18}
            className={exact ? 'text-signal-400' : 'text-caution-400'}
            aria-hidden="true"
          />
          <div>
            <div
              className={`text-xs font-medium ${exact ? 'text-signal-400' : 'text-caution-400'}`}
            >
              {exact
                ? 'Aggregate parity exact: Σ|Δ| = 0'
                : `Aggregate drift detected: Σ|Δ| = ${formatInt(totalDelta)}`}
            </div>
            <p className="mt-0.5 text-xs text-slate-400">
              GROUP BY <span className="tabular">{chart.category_column}</span>,
              measure <span className="tabular">{chart.measure_column}</span> ·{' '}
              {merged.length} buckets compared
            </p>
          </div>
        </div>
        <div className="tabular flex gap-4 text-xs text-slate-400">
          <span>
            max |Δ|{' '}
            <span className={maxDelta === 0 ? 'text-signal-400 font-medium' : 'text-caution-400 font-medium'}>
              {formatInt(maxDelta)}
            </span>
          </span>
          <span>
            buckets <span className="text-slate-200">{merged.length}</span>
          </span>
        </div>
      </m.div>

      {/* Mode switch */}
      <div
        className="flex w-fit gap-1 rounded-lg border border-white/8 bg-abyss-900 p-1"
        role="tablist"
        aria-label="Chart type"
      >
        {(
          [
            { id: 'bars', label: 'Aggregates', Icon: BarChart3 },
            { id: 'trend', label: 'Trend', Icon: LineIcon },
          ] as const
        ).map(({ id, label, Icon }) => {
          const active = mode === id;
          return (
            <button
              key={id}
              type="button"
              role="tab"
              aria-selected={active}
              onClick={() => setMode(id)}
              className={`relative rounded-md px-3 py-1.5 text-xs font-medium outline-none transition-colors ${
                active
                  ? 'bg-slate-100 text-abyss-950 font-medium shadow-xs'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <span className="flex items-center gap-1.5">
                <Icon size={13} aria-hidden="true" />
                {label}
              </span>
            </button>
          );
        })}
      </div>

      {/* Chart surface */}
      <div className="h-[320px] w-full rounded-xl border border-white/8 bg-abyss-900/40 p-4">
        <AnimatePresence mode="wait" initial={false}>
          <m.div
            key={mode}
            variants={fadeVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
            className="h-full w-full"
          >
            <ResponsiveContainer width="100%" height="100%">
              {mode === 'bars' ? (
                <BarChart
                  data={merged}
                  margin={{ top: 8, right: 12, bottom: 4, left: 4 }}
                  barGap={-14}
                >
                  <CartesianGrid stroke={COLOR_GRID} strokeDasharray="3 3" vertical={false} />
                  <XAxis
                    dataKey="originalName"
                    tick={{ fill: COLOR_AXIS, fontSize: 11 }}
                    tickLine={false}
                    axisLine={{ stroke: COLOR_GRID }}
                    interval={0}
                    height={42}
                    angle={-18}
                    textAnchor="end"
                  />
                  <YAxis
                    tick={{ fill: COLOR_AXIS, fontSize: 11 }}
                    tickLine={false}
                    axisLine={{ stroke: COLOR_GRID }}
                    tickFormatter={(v: number) => formatCompact(v)}
                    width={52}
                  />
                  <Tooltip
                    content={<ParityTooltip />}
                    cursor={{ fill: 'rgb(45 212 191 / 0.05)' }}
                  />
                  <Legend
                    wrapperStyle={{ fontSize: 12, color: COLOR_AXIS }}
                    iconType="circle"
                    iconSize={7}
                  />
                  {/* Wide translucent bar = confidential baseline */}
                  <Bar
                    dataKey="confidential"
                    name="Confidential"
                    fill={COLOR_CLASSIFIED}
                    fillOpacity={0.25}
                    stroke={COLOR_CLASSIFIED}
                    strokeWidth={1}
                    barSize={24}
                    radius={[3, 3, 0, 0]}
                    isAnimationActive={false}
                  />
                  {/* Narrow solid bar = sanitized, superimposed */}
                  <Bar
                    dataKey="sanitized"
                    name="Sanitized"
                    barSize={10}
                    radius={[3, 3, 0, 0]}
                    isAnimationActive={false}
                  >
                    {merged.map((point) => (
                      <Cell
                        key={point.index}
                        fill={point.delta === 0 ? COLOR_SIGNAL : '#f59e0b'}
                      />
                    ))}
                  </Bar>
                </BarChart>
              ) : (
                <LineChart
                  data={merged}
                  margin={{ top: 8, right: 12, bottom: 4, left: 4 }}
                >
                  <CartesianGrid stroke={COLOR_GRID} strokeDasharray="3 3" vertical={false} />
                  <XAxis
                    dataKey="originalName"
                    tick={{ fill: COLOR_AXIS, fontSize: 11 }}
                    tickLine={false}
                    axisLine={{ stroke: COLOR_GRID }}
                    interval={0}
                    height={42}
                    angle={-18}
                    textAnchor="end"
                  />
                  <YAxis
                    tick={{ fill: COLOR_AXIS, fontSize: 11 }}
                    tickLine={false}
                    axisLine={{ stroke: COLOR_GRID }}
                    tickFormatter={(v: number) => formatCompact(v)}
                    width={52}
                  />
                  <Tooltip content={<ParityTooltip />} />
                  <Legend
                    wrapperStyle={{ fontSize: 12, color: COLOR_AXIS }}
                    iconType="circle"
                    iconSize={7}
                  />
                  <Line
                    type="monotone"
                    dataKey="confidential"
                    name="Confidential"
                    stroke={COLOR_CLASSIFIED}
                    strokeWidth={3}
                    dot={{ fill: COLOR_CLASSIFIED, r: 3 }}
                    isAnimationActive={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="sanitized"
                    name="Sanitized"
                    stroke={COLOR_SIGNAL}
                    strokeWidth={2}
                    strokeDasharray="4 3"
                    dot={{ fill: COLOR_SIGNAL, r: 2 }}
                    isAnimationActive={false}
                  />
                </LineChart>
              )}
            </ResponsiveContainer>
          </m.div>
        </AnimatePresence>
      </div>
    </div>
  );
}
