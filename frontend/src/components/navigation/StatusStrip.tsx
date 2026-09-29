import { AnimatePresence, m } from 'motion/react';
import { Activity } from 'lucide-react';
import type { Variants } from 'motion/react';
import { Alert } from '../ui/Primitives';

export interface StatusStripProps {
  busy: string | null;
  error: string | null;
  notice: string | null;
  revealVariants: Variants;
  onDismissError: () => void;
  onDismissNotice: () => void;
}

export function StatusStrip({
  busy,
  error,
  notice,
  revealVariants,
  onDismissError,
  onDismissNotice,
}: StatusStripProps) {
  return (
    <div className="mx-auto max-w-[1600px] px-6">
      <AnimatePresence mode="popLayout">
        {busy ? (
          <m.div
            key="busy"
            variants={revealVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
            className="mt-4 flex items-center gap-3 rounded-xl border border-signal-500/20 bg-signal-500/5 px-4 py-2.5"
            role="status"
            aria-live="polite"
          >
            <Activity size={14} className="shrink-0 text-signal-400" aria-hidden="true" />
            <span className="text-xs text-signal-400">{busy}</span>
          </m.div>
        ) : null}

        {error ? (
          <m.div key="error" className="mt-4" layout>
            <Alert tone="error" title="Operation failed" onDismiss={onDismissError}>
              {error}
            </Alert>
          </m.div>
        ) : null}

        {notice ? (
          <m.div key="notice" className="mt-4" layout>
            <Alert tone="info" title="Ready" onDismiss={onDismissNotice}>
              {notice}
            </Alert>
          </m.div>
        ) : null}
      </AnimatePresence>
    </div>
  );
}
