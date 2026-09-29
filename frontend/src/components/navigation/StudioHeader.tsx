import { Layers, RefreshCw, Search, ShieldCheck } from 'lucide-react';
import type { Stage } from '../../lib/types';
import type { EgressLedger } from '../../hooks/useEgressWatch';
import { Button } from '../ui/Primitives';
import { Kbd } from '../ui/Toasts';
import { StageRail } from './StageRail';

export interface StudioHeaderProps {
  setPaletteOpen: (open: boolean) => void;
  setShowAttestation: (show: boolean) => void;
  egress: EgressLedger;
  resetAll: () => void;
  stage: Stage;
  onJump: (s: Stage) => void;
  reachable: Set<Stage>;
}

export function StudioHeader({
  setPaletteOpen,
  setShowAttestation,
  egress,
  resetAll,
  stage,
  onJump,
  reachable,
}: StudioHeaderProps) {
  return (
    <header className="sticky top-0 z-40 border-b border-white/8 bg-abyss-950/90 backdrop-blur-md">
      <div className="mx-auto flex max-w-[1600px] flex-wrap items-center justify-between gap-3 px-6 py-3.5">
        <div className="flex items-center gap-3">
          <span
            className="flex size-8 items-center justify-center rounded-lg border border-white/8 bg-abyss-900 text-signal-400"
            aria-hidden="true"
          >
            <Layers size={16} />
          </span>
          <div>
            <h1 className="text-sm font-medium leading-tight text-slate-100">
              AetherMask{' '}
              <span className="font-normal text-slate-500">· CipherShift</span>
            </h1>
            <p className="text-xs text-slate-400">
              Offline semantic obfuscation &amp; lossless de-anonymization
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setPaletteOpen(true)}
            className="hidden items-center gap-2 rounded-lg border border-white/8 bg-abyss-850 px-2.5 py-1.5 text-xs text-slate-300 outline-none hover:border-white/16 hover:bg-abyss-800 transition-colors sm:flex"
            title="Open command palette"
            aria-keyshortcuts="Control+K Meta+K"
          >
            <Search size={13} className="text-slate-400" aria-hidden="true" />
            <span>Commands</span>
            <Kbd>Ctrl K</Kbd>
          </button>

          <button
            type="button"
            onClick={() => setShowAttestation(true)}
            className="flex items-center gap-2 rounded-lg border border-white/8 bg-abyss-850 px-2.5 py-1.5 text-xs font-normal text-slate-300 outline-none hover:border-white/16 hover:bg-abyss-800 transition-colors"
            title="Open air-gap attestation report"
          >
            <span
              className={`size-1.5 rounded-full ${
                egress.external.length === 0 ? 'bg-signal-400' : 'bg-classified-400'
              }`}
              aria-hidden="true"
            />
            <ShieldCheck size={13} className="text-slate-400" aria-hidden="true" />
            <span>
              {egress.external.length === 0
                ? 'Air-gapped'
                : `${egress.external.length} external call(s)`}
            </span>
          </button>

          <Button tone="ghost" icon={<RefreshCw size={13} />} onClick={resetAll}>
            Reset
          </Button>
        </div>
      </div>

      <div className="mx-auto max-w-[1600px] px-6 pb-3">
        <StageRail stage={stage} onJump={onJump} reachable={reachable} />
      </div>
    </header>
  );
}
