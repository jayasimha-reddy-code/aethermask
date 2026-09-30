/**
 * AetherMask (CipherShift) :: DataGrid
 *
 * A sortable, filterable, paginated preview grid built on TanStack Table v9.
 *
 * TanStack v9 notes (this is a ground-up rewrite of v8):
 *   - `useReactTable`      -> `useTable`
 *   - `getCoreRowModel()`  -> `createCoreRowModel()`
 *   - row models and feature modules are registered together through
 *     `tableFeatures({...})`, which is passed as the `features` option.
 *   - Features are opt-in: `getVisibleCells()` only exists once
 *     `columnVisibilityFeature` is registered.
 */

import { useMemo, useState } from 'react';
import {
  columnFilteringFeature,
  columnVisibilityFeature,
  createColumnHelper,
  createCoreRowModel,
  createFilteredRowModel,
  createPaginatedRowModel,
  createSortedRowModel,
  flexRender,
  rowPaginationFeature,
  rowSortingFeature,
  tableFeatures,
  useTable,
  type SortingState,
} from '@tanstack/react-table';
import { m } from 'motion/react';
import {
  ArrowDown,
  ArrowUp,
  ChevronLeft,
  ChevronRight,
  ChevronsUpDown,
  Search,
} from 'lucide-react';
import type { FramePreview, GridCellValue, GridRow } from '../../lib/types';
import { displayCell, formatInt } from '../../lib/format';
import { easeQuick, listItemVariants, listVariants } from '../../lib/motion';
import { inputClass } from '../ui/Primitives';

const gridFeatures = tableFeatures({
  rowSortingFeature,
  columnFilteringFeature,
  columnVisibilityFeature,
  rowPaginationFeature,
  coreRowModel: createCoreRowModel(),
  sortedRowModel: createSortedRowModel(),
  filteredRowModel: createFilteredRowModel(),
  paginatedRowModel: createPaginatedRowModel(),
});

const columnHelper = createColumnHelper<typeof gridFeatures, GridRow>();

type GridColumns = NonNullable<
  Parameters<typeof useTable<typeof gridFeatures, GridRow>>[0]['columns']
>;

export interface DataGridProps {
  frame: FramePreview;
  /** Accent used for header text - distinguishes source vs sanitized. */
  tone?: 'classified' | 'signal' | 'neutral';
  /** Highlight these column names as transformed. */
  highlight?: Set<string>;
  pageSize?: number;
  /** Show the per-grid search box. */
  searchable?: boolean;
  emptyLabel?: string;
}

function buildGridRecords(frame?: FramePreview): GridRow[] {
  const cols = Array.isArray(frame?.columns) ? frame.columns : [];
  const rows = Array.isArray(frame?.rows) ? frame.rows : [];
  return rows.map((row) => {
    const record: GridRow = {};
    cols.forEach((col, i) => {
      const colName = col != null ? String(col) : '';
      const key = colName.trim() ? colName : `col_${i + 1}`;
      record[key] = row?.[i] ?? null;
      if (colName && colName !== key) {
        record[colName] = row?.[i] ?? null;
      }
    });
    return record;
  });
}

function buildGridColumns(frame?: FramePreview): GridColumns {
  const seen = new Set<string>();
  const cols = Array.isArray(frame?.columns) ? frame.columns : [];
  const dtypes = Array.isArray(frame?.dtypes) ? frame.dtypes : [];

  return cols.map((rawCol, i) => {
    const colName = rawCol != null ? String(rawCol) : '';
    let colId = colName.trim() ? colName : `col_${i + 1}`;
    if (seen.has(colId)) {
      colId = `${colId}_${i + 1}`;
    }
    seen.add(colId);

    return columnHelper.accessor(
      (row) => row[colId] ?? (colName ? row[colName] : null),
      {
        id: colId,
        header: colName.trim() || `(Column ${i + 1})`,
        meta: { dtype: dtypes[i] ?? '' },
        cell: (ctx) => displayCell(ctx.getValue() as GridCellValue),
      },
    );
  }) as unknown as GridColumns;
}

function filterGridRows(data: GridRow[], query: string): GridRow[] {
  const q = query.trim().toLowerCase();
  if (!q) return data;
  return data.filter((row) =>
    Object.values(row).some((v) =>
      v === null ? false : String(v).toLowerCase().includes(q),
    ),
  );
}

export function DataGrid({
  frame,
  tone = 'neutral',
  highlight,
  pageSize = 12,
  searchable = true,
  emptyLabel = 'No rows in preview',
}: DataGridProps) {
  const [sorting, setSorting] = useState<SortingState>([]);
  const [query, setQuery] = useState('');
  const [pagination, setPagination] = useState({ pageIndex: 0, pageSize });

    // Convert the server's column/row arrays into records once per frame.
  const data = useMemo<GridRow[]>(() => buildGridRecords(frame), [frame]);

  const columns = useMemo<GridColumns>(() => buildGridColumns(frame), [frame]);

  // Client-side global filter across every visible cell.
  const filtered = useMemo(() => filterGridRows(data, query), [data, query]);

  const table = useTable({
    features: gridFeatures,
    columns,
    data: filtered,
    state: { sorting, pagination },
    onSortingChange: setSorting,
    onPaginationChange: setPagination,
  });

  const headTone =
    tone === 'classified'
      ? 'text-classified-400'
      : tone === 'signal'
        ? 'text-signal-400'
        : 'text-slate-300';

  const rows = table.getRowModel().rows;
  const pageCount = Math.max(1, Math.ceil(filtered.length / pagination.pageSize));

  return (
    <div className="flex h-full flex-col">
      {searchable ? (
        <div className="flex items-center gap-2 border-b border-abyss-700 px-3 py-2">
          <Search size={13} className="shrink-0 text-slate-500" aria-hidden="true" />
          <input
            type="search"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setPagination((p) => ({ ...p, pageIndex: 0 }));
            }}
            placeholder={`Filter ${formatInt(data.length)} preview rows…`}
            aria-label="Filter preview rows"
            className="w-full bg-transparent py-0.5 text-xs text-slate-200 outline-none placeholder:text-slate-600"
          />
          {query ? (
            <span className="tabular shrink-0 text-[11px] text-slate-500">
              {formatInt(filtered.length)} match
            </span>
          ) : null}
        </div>
      ) : null}

      <div className="min-h-0 flex-1 overflow-auto">
        <table className="w-full border-collapse text-left">
          <thead className="sticky top-0 z-10 bg-abyss-850/95 backdrop-blur">
            {table.getHeaderGroups().map((hg) => (
              <tr key={hg.id}>
                {hg.headers.map((header) => {
                  const id = header.column.id;
                  const isHot = highlight?.has(id) ?? false;
                  const sorted = header.column.getIsSorted();
                  const dtype =
                    (header.column.columnDef.meta as { dtype?: string } | undefined)
                      ?.dtype ?? '';
                  return (
                    <th
                      key={header.id}
                      scope="col"
                      className="border-b border-abyss-700 px-3 py-2 align-bottom whitespace-nowrap"
                      aria-sort={
                        sorted === 'asc'
                          ? 'ascending'
                          : sorted === 'desc'
                            ? 'descending'
                            : 'none'
                      }
                    >
                      <button
                        type="button"
                        onClick={header.column.getToggleSortingHandler()}
                        className="group flex w-full flex-col items-start gap-0.5 rounded outline-none"
                        title={`Sort by ${id}`}
                      >
                        <span className="flex items-center gap-1">
                          <span
                            className={`text-[11px] font-semibold tracking-wide ${isHot ? 'text-caution-400' : headTone}`}
                          >
                            {flexRender(
                              header.column.columnDef.header,
                              header.getContext(),
                            )}
                          </span>
                          <span className="text-slate-600 group-hover:text-slate-400">
                            {sorted === 'asc' ? (
                              <ArrowUp size={10} />
                            ) : sorted === 'desc' ? (
                              <ArrowDown size={10} />
                            ) : (
                              <ChevronsUpDown size={10} className="opacity-0 group-hover:opacity-100" />
                            )}
                          </span>
                        </span>
                        {dtype ? (
                          <span className="text-[9px] font-normal tracking-wide text-slate-600 uppercase">
                            {dtype}
                          </span>
                        ) : null}
                      </button>
                    </th>
                  );
                })}
              </tr>
            ))}
          </thead>

          <m.tbody variants={listVariants} initial="hidden" animate="visible">
            {rows.length === 0 ? (
              <tr>
                <td
                  colSpan={Math.max(1, frame?.columns?.length ?? 1)}
                  className="px-3 py-10 text-center text-xs text-slate-500"
                >
                  {emptyLabel}
                </td>
              </tr>
            ) : (
              rows.map((row) => (
                <m.tr
                  key={row.id}
                  variants={listItemVariants}
                  className="border-b border-abyss-800/70 hover:bg-abyss-800/40"
                >
                  {row.getVisibleCells().map((cell) => {
                    const isHot = highlight?.has(cell.column.id) ?? false;
                    return (
                      <td
                        key={cell.id}
                        className={`tabular max-w-[22ch] truncate px-3 py-1.5 text-[11.5px] ${isHot ? 'text-caution-400/90' : 'text-slate-300'}`}
                        title={displayCell(cell.getValue() as GridRow[string])}
                      >
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </td>
                    );
                  })}
                </m.tr>
              ))
            )}
          </m.tbody>
        </table>
      </div>

      <div className="flex items-center justify-between gap-3 border-t border-abyss-700 px-3 py-2">
        <span className="tabular text-[11px] text-slate-500">
          Showing {formatInt(rows.length)} of {formatInt(filtered.length)}
          {' · '}
          {formatInt(frame?.total_rows ?? 0)} total rows × {frame?.total_columns ?? 0} cols
        </span>
        <div className="flex items-center gap-1.5">
          <m.button
            type="button"
            onClick={() =>
              setPagination((p) => ({
                ...p,
                pageIndex: Math.max(0, p.pageIndex - 1),
              }))
            }
            disabled={pagination.pageIndex === 0}
            className="rounded-md border border-abyss-700 p-1 text-slate-400 outline-none disabled:opacity-35 enabled:hover:border-abyss-600 enabled:hover:text-slate-100"
            aria-label="Previous page"
            whileTap={pagination.pageIndex === 0 ? undefined : { scale: 0.92 }}
            transition={easeQuick}
          >
            <ChevronLeft size={13} />
          </m.button>
          <span className="tabular min-w-[5.5rem] text-center text-[11px] text-slate-400">
            Page {pagination.pageIndex + 1} / {pageCount}
          </span>
          <m.button
            type="button"
            onClick={() =>
              setPagination((p) => ({
                ...p,
                pageIndex: Math.min(pageCount - 1, p.pageIndex + 1),
              }))
            }
            disabled={pagination.pageIndex >= pageCount - 1}
            className="rounded-md border border-abyss-700 p-1 text-slate-400 outline-none disabled:opacity-35 enabled:hover:border-abyss-600 enabled:hover:text-slate-100"
            aria-label="Next page"
            whileTap={
              pagination.pageIndex >= pageCount - 1 ? undefined : { scale: 0.92 }
            }
            transition={easeQuick}
          >
            <ChevronRight size={13} />
          </m.button>
        </div>
      </div>
    </div>
  );
}

/** Small controlled search input reused by stage headers. */
export function SearchInput({
  value,
  onChange,
  placeholder,
  label,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  label: string;
}) {
  return (
    <div className="relative">
      <Search
        size={13}
        className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-slate-500"
        aria-hidden="true"
      />
      <input
        type="search"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        aria-label={label}
        className={`${inputClass} pl-8`}
      />
    </div>
  );
}
