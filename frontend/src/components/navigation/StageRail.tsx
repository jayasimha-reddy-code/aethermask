import {
  ArrowLeftRight,
  CheckCircle2,
  Database,
  RotateCcw,
  ScanLine,
  ScanSearch,
  Vault,
} from 'lucide-react';
import type { Stage } from '../../lib/types';

export const STAGES: {
  id: Stage;
  label: string;
  Icon: typeof Database;
  blurb: string;
}[] = [
  { id: 'ingest', label: 'Ingest', Icon: Database, blurb: 'Load source dataset' },
  { id: 'profile', label: 'Profile', Icon: ScanSearch, blurb: 'Analyze sensitivity' },
  { id: 'transform', label: 'Transform', Icon: ArrowLeftRight, blurb: 'Cover domain projection' },
  { id: 'export', label: 'Vault', Icon: Vault, blurb: 'Cryptographic vault' },
  { id: 'restore', label: 'Restore', Icon: RotateCcw, blurb: 'Lossless de-anonymization' },
  { id: 'audit', label: 'Audit', Icon: ScanLine, blurb: 'Independent verification' },
];

export const STAGE_INDEX: Record<Stage, number> = {
  ingest: 0,
  profile: 1,
  transform: 2,
  export: 3,
  restore: 4,
  audit: 5,
};

export interface StageRailProps {
  stage: Stage;
  onJump: (s: Stage) => void;
  reachable: Set<Stage>;
}

export function StageRail({ stage, onJump, reachable }: StageRailProps) {
  return (
    <nav aria-label="Pipeline stage" className="w-full">
      <ol className="flex items-stretch gap-2 overflow-x-auto pb-1">
        {STAGES.map(({ id, label, Icon, blurb }, i) => {
          const active = id === stage;
          const done = STAGE_INDEX[id] < STAGE_INDEX[stage];
          const available = reachable.has(id);
          return (
            <li key={id} className="min-w-0 flex-1">
              <button
                type="button"
                onClick={() => available && onJump(id)}
                disabled={!available}
                aria-current={active ? 'step' : undefined}
                className={`relative flex w-full items-center gap-2.5 overflow-hidden rounded-lg border px-3 py-2 text-left outline-none transition-colors duration-150 ${
                  active
                    ? 'border-signal-500/40 bg-signal-500/8'
                    : available
                      ? 'cursor-pointer border-white/8 bg-abyss-850/60 hover:border-white/16 hover:bg-abyss-800/60'
                      : 'cursor-not-allowed border-white/4 bg-abyss-900/30 opacity-40'
                }`}
              >
                {active ? (
                  <span
                    className="absolute inset-x-0 bottom-0 h-0.5 bg-signal-500"
                    aria-hidden="true"
                  />
                ) : null}

                <span
                  className={`flex size-6 shrink-0 items-center justify-center rounded-md ${
                    active
                      ? 'bg-signal-500 text-abyss-950 font-medium'
                      : done
                        ? 'bg-signal-500/15 text-signal-400'
                        : 'bg-abyss-800 text-slate-500'
                  }`}
                  aria-hidden="true"
                >
                  {done && !active ? (
                    <CheckCircle2 size={13} />
                  ) : (
                    <Icon size={13} />
                  )}
                </span>

                <span className="min-w-0 flex-1">
                  <span
                    className={`block truncate text-xs font-medium ${
                      active ? 'text-signal-400' : 'text-slate-200'
                    }`}
                  >
                    <span className="tabular mr-1 text-slate-500">{i + 1}</span>
                    {label}
                  </span>
                  <span className="hidden truncate text-[11px] text-slate-500 lg:block">
                    {blurb}
                  </span>
                </span>
              </button>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
