/**
 * AetherMask (CipherShift) :: ProfilePanel
 *
 * Renders the sensitivity profiler's verdict: risk grade, per-category finding
 * counts, and an expandable per-column breakdown.
 *
 * All evidence fragments arrive from the server already redacted,
 * so nothing classified is echoed into the DOM at this stage.
 */

import { useMemo, useState } from 'react';
import { AnimatePresence, m } from 'motion/react';
import {
  AlertOctagon,
  ChevronRight,
  Database,
  KeyRound,
} from 'lucide-react';
import type { ColumnProfileInfo, ProfileResponse } from '../../lib/types';
import {
  formatInt,
  formatPct,
  severityLabel,
} from '../../lib/format';
import { easeQuick } from '../../lib/motion';
import { Badge, MeterBar, Stat } from '../ui/Primitives';
import { SearchInput } from '../grid/DataGrid';

function severityTone(
  severity: number,
): 'classified' | 'caution' | 'vault' | 'muted' {
  if (severity >= 5) return 'classified';
  if (severity >= 4) return 'caution';
  if (severity >= 2) return 'vault';
  return 'muted';
}

function ColumnRow({ column }: { column: ColumnProfileInfo }) {
  const [open, setOpen] = useState(false);
  const hasFindings = column.findings.length > 0;

  return (
    <div className="border-t border-white/6">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex w-full items-center gap-3 px-4 py-2.5 text-left outline-none hover:bg-abyss-800/40 transition-colors"
      >
        <span
          className={`shrink-0 text-slate-500 transition-transform duration-150 ${open ? 'rotate-90' : ''}`}
          aria-hidden="true"
        >
          <ChevronRight size={13} />
        </span>

        <span className="tabular min-w-0 flex-1 truncate text-xs text-slate-200">
          {column.name}
          {column.is_unique ? (
            <KeyRound
              size={11}
              className="ml-1.5 inline text-vault-400"
              aria-label="Primary key candidate"
            />
          ) : null}
        </span>

        <span className="hidden w-20 shrink-0 text-xs text-slate-500 sm:block">
          {column.dtype}
        </span>
        <span className="hidden w-28 shrink-0 truncate text-xs text-slate-500 md:block">
          {column.semantic_role}
        </span>
        <span className="tabular hidden w-16 shrink-0 text-right text-xs text-slate-500 lg:block">
          {formatInt(column.distinct_count)}
        </span>

        <span className="w-24 shrink-0 text-right">
          {hasFindings ? (
            <Badge tone={severityTone(column.max_severity)}>
              {severityLabel(column.max_severity)}
            </Badge>
          ) : (
            <span className="text-xs text-slate-500">Clean</span>
          )}
        </span>
      </button>

      <AnimatePresence initial={false}>
        {open ? (
          <m.div
            key="detail"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={easeQuick}
            className="overflow-hidden bg-abyss-900/60"
          >
            <div className="space-y-3 px-4 py-3 pl-10">
              <dl className="tabular grid grid-cols-2 gap-x-6 gap-y-1 text-xs sm:grid-cols-4">
                <div>
                  <dt className="text-slate-500">Rows</dt>
                  <dd className="text-slate-300">{formatInt(column.row_count)}</dd>
                </div>
                <div>
                  <dt className="text-slate-500">Distinct</dt>
                  <dd className="text-slate-300">
                    {formatInt(column.distinct_count)}
                  </dd>
                </div>
                <div>
                  <dt className="text-slate-500">Nulls</dt>
                  <dd className="text-slate-300">{formatInt(column.null_count)}</dd>
                </div>
                <div>
                  <dt className="text-slate-500">Cardinality</dt>
                  <dd className="text-slate-300">
                    {formatPct(column.cardinality_ratio)}
                  </dd>
                </div>
              </dl>

              {column.numeric_stats ? (
                <dl className="tabular grid grid-cols-2 gap-x-6 gap-y-1 rounded-lg border border-white/8 bg-abyss-850/60 p-3 text-xs sm:grid-cols-4">
                  {Object.entries(column.numeric_stats)
                    .slice(0, 8)
                    .map(([k, v]) => (
                      <div key={k}>
                        <dt className="text-slate-500">{k}</dt>
                        <dd className="text-slate-300">
                          {typeof v === 'number'
                            ? Number.isInteger(v)
                              ? formatInt(v)
                              : v.toFixed(3)
                            : String(v)}
                        </dd>
                      </div>
                    ))}
                </dl>
              ) : null}

              {column.top_categories.length > 0 ? (
                <div>
                  <div className="mb-1 text-xs text-slate-500">
                    Top values (labels redacted, counts exact)
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {column.top_categories.slice(0, 8).map((cat, i) => (
                      <Badge key={`${cat.value}-${i}`} tone="muted">
                        <span className="tabular">{cat.value ?? '∅'}</span>
                        <span className="text-slate-500">
                          ×{formatInt(cat.count)}
                        </span>
                      </Badge>
                    ))}
                  </div>
                </div>
              ) : null}

              {hasFindings ? (
                <ul className="space-y-1.5">
                  {column.findings.map((f, i) => (
                    <li
                      key={`${f.rule_id}-${i}`}
                      className="rounded-lg border border-white/8 bg-abyss-850/60 p-3"
                    >
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge tone={severityTone(f.severity)}>{f.rule_id}</Badge>
                        <span className="text-xs text-slate-500">
                          {f.category} · matched in {f.matched_in.join(', ')}
                        </span>
                      </div>
                      <p className="mt-1 text-xs leading-relaxed text-slate-400">
                        {f.explanation}
                      </p>
                      {f.evidence.length > 0 ? (
                        <p className="tabular mt-1 text-xs text-slate-500">
                          Evidence: {f.evidence.slice(0, 3).join(' · ')}
                        </p>
                      ) : null}
                    </li>
                  ))}
                </ul>
              ) : null}
            </div>
          </m.div>
        ) : null}
      </AnimatePresence>
    </div>
  );
}

export function ProfilePanel({ profile }: { profile: ProfileResponse }) {
  const [query, setQuery] = useState('');
  const [onlyFindings, setOnlyFindings] = useState(false);

  const allColumns = useMemo(
    () => profile.tables.flatMap((t) => t.columns),
    [profile.tables],
  );

  const allFindings = useMemo(
    () => allColumns.flatMap((c) => c.findings),
    [allColumns],
  );

  const candidateKeys = useMemo(
    () => profile.tables.flatMap((t) => t.primary_key_candidates),
    [profile.tables],
  );

  const findingEntries = useMemo(
    () =>
      Object.entries(profile.finding_summary ?? {}).sort((a, b) => b[1] - a[1]),
    [profile.finding_summary],
  );

  const maxFinding = findingEntries[0]?.[1] ?? 1;

  return (
    <div className="space-y-5">
      {/* Risk verdict */}
      <div className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-white/8 bg-abyss-850/60 p-4">
        <div className="flex items-center gap-4">
          <AlertOctagon size={24} className="text-classified-400" aria-hidden="true" />
          <div>
            <div className="flex items-baseline gap-2">
              <span className="text-xl font-medium text-slate-100">
                Risk Grade {profile.risk_grade}
              </span>
              <span className="text-xs text-slate-400">
                (score {profile.risk_score.toFixed(1)} / 100)
              </span>
            </div>
            <p className="mt-0.5 text-xs text-slate-400">
              Evaluated across {formatInt(profile.table_count)} table(s) and {formatInt(allColumns.length)} column(s)
            </p>
          </div>
        </div>
        {profile.recommended_profile ? (
          <div className="text-right">
            <div className="text-xs text-slate-500">Recommended cover domain</div>
            <div className="text-xs font-medium text-signal-400">
              {profile.recommended_profile}
            </div>
          </div>
        ) : null}
      </div>

      {/* Dataset headline stats */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Stat
          label="Total rows"
          value={formatInt(profile.total_rows)}
          icon={<Database size={13} />}
        />
        <Stat
          label="Columns scanned"
          value={formatInt(allColumns.length)}
        />
        <Stat
          label="Sensitive findings"
          value={formatInt(allFindings.length)}
        />
        <Stat
          label="Candidate keys"
          value={formatInt(candidateKeys.length)}
          icon={<KeyRound size={13} />}
        />
      </div>

      {/* Finding category bars */}
      {findingEntries.length > 0 ? (
        <div className="rounded-xl border border-white/8 bg-abyss-850/60 p-4">
          <h3 className="mb-3 text-xs font-medium text-slate-300">
            Findings by category
          </h3>
          <div className="space-y-2">
            {findingEntries.map(([cat, count]) => (
              <div key={cat} className="flex items-center gap-3 text-xs">
                <span className="w-32 shrink-0 truncate text-slate-400">
                  {cat}
                </span>
                <div className="min-w-0 flex-1">
                  <MeterBar value={count} max={maxFinding} tone="classified" />
                </div>
                <span className="tabular w-10 shrink-0 text-right text-slate-300">
                  {formatInt(count)}
                </span>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {/* Column breakdown */}
      <div className="overflow-hidden rounded-xl border border-white/8 bg-abyss-850/40">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/8 bg-abyss-850/80 px-4 py-3">
          <div className="flex items-center gap-3">
            <h3 className="text-xs font-medium text-slate-200">
              Per-column breakdown
            </h3>
            <span className="text-xs text-slate-500">
              {allColumns.length} columns
            </span>
          </div>
          <div className="flex items-center gap-3">
            <label className="flex cursor-pointer items-center gap-1.5 text-xs text-slate-400">
              <input
                type="checkbox"
                checked={onlyFindings}
                onChange={(e) => setOnlyFindings(e.target.checked)}
                className="rounded border-white/12 bg-abyss-900 text-signal-500 focus:ring-0"
              />
              Findings only
            </label>
            <div className="w-48">
              <SearchInput
                value={query}
                onChange={setQuery}
                placeholder="Filter columns…"
                label="Filter columns"
              />
            </div>
          </div>
        </div>

        <div className="max-h-[460px] overflow-auto">
          {allColumns
            .filter((c: ColumnProfileInfo) => {
              if (onlyFindings && c.findings.length === 0) return false;
              if (!query) return true;
              return (
                c.name.toLowerCase().includes(query.toLowerCase()) ||
                c.semantic_role.toLowerCase().includes(query.toLowerCase())
              );
            })
            .map((col: ColumnProfileInfo) => (
              <ColumnRow key={col.name} column={col} />
            ))}
        </div>
      </div>
    </div>
  );
}
