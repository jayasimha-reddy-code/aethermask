/**
 * AetherMask (CipherShift) :: toast notifications
 *
 * Restrained, quiet surface notifications with hairline borders.
 */

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import { AnimatePresence, m, useReducedMotion } from 'motion/react';
import { AlertTriangle, CheckCircle2, Info, ShieldAlert, X } from 'lucide-react';
import { easeQuick } from '../../lib/motion';

export type ToastTone = 'success' | 'error' | 'info' | 'warning';

export interface Toast {
  id: number;
  tone: ToastTone;
  title: string;
  body?: string;
  /** ms; 0 keeps the toast until dismissed. Errors default to sticky. */
  ttl?: number;
}

interface ToastApi {
  push: (t: Omit<Toast, 'id'>) => number;
  dismiss: (id: number) => void;
  success: (title: string, body?: string) => number;
  error: (title: string, body?: string) => number;
  info: (title: string, body?: string) => number;
  warning: (title: string, body?: string) => number;
}

const ToastContext = createContext<ToastApi | null>(null);

export function useToasts(): ToastApi {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToasts must be used inside <ToastProvider>');
  return ctx;
}

const TONE = {
  success: {
    Icon: CheckCircle2,
    iconCls: 'text-signal-400',
    cls: 'border-signal-500/30 bg-abyss-900/95 text-slate-200',
  },
  error: {
    Icon: ShieldAlert,
    iconCls: 'text-classified-400',
    cls: 'border-classified-500/30 bg-abyss-900/95 text-slate-200',
  },
  warning: {
    Icon: AlertTriangle,
    iconCls: 'text-caution-400',
    cls: 'border-caution-500/30 bg-abyss-900/95 text-slate-200',
  },
  info: {
    Icon: Info,
    iconCls: 'text-slate-400',
    cls: 'border-white/8 bg-abyss-900/95 text-slate-200',
  },
} as const;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const seq = useRef(0);
  const timers = useRef(new Map<number, number>());
  const paused = useRef(false);
  const reduce = useReducedMotion();

  const dismiss = useCallback((id: number) => {
    const t = timers.current.get(id);
    if (t) {
      window.clearTimeout(t);
      timers.current.delete(id);
    }
    setToasts((list) => list.filter((x) => x.id !== id));
  }, []);

  const arm = useCallback(
    (id: number, ttl: number) => {
      if (ttl <= 0) return;
      const handle = window.setTimeout(() => {
        if (paused.current) {
          arm(id, 1200);
          return;
        }
        dismiss(id);
      }, ttl);
      timers.current.set(id, handle);
    },
    [dismiss],
  );

  const push = useCallback(
    (t: Omit<Toast, 'id'>) => {
      seq.current += 1;
      const id = seq.current;
      const ttl = t.ttl ?? (t.tone === 'error' ? 0 : 5000);
      setToasts((list) => [...list.slice(-4), { ...t, id }]);
      arm(id, ttl);
      return id;
    },
    [arm],
  );

  const api = useMemo<ToastApi>(
    () => ({
      push,
      dismiss,
      success: (title, body) => push({ tone: 'success', title, body }),
      error: (title, body) => push({ tone: 'error', title, body }),
      info: (title, body) => push({ tone: 'info', title, body }),
      warning: (title, body) => push({ tone: 'warning', title, body }),
    }),
    [push, dismiss],
  );

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div
        className="pointer-events-none fixed right-4 bottom-4 z-[70] flex w-full max-w-sm flex-col gap-2"
        onMouseEnter={() => {
          paused.current = true;
        }}
        onMouseLeave={() => {
          paused.current = false;
        }}
        onFocusCapture={() => {
          paused.current = true;
        }}
        onBlurCapture={() => {
          paused.current = false;
        }}
      >
        <AnimatePresence initial={false} mode="popLayout">
          {toasts.map((t) => {
            const { Icon, cls, iconCls } = TONE[t.tone];
            return (
              <m.div
                key={t.id}
                layout
                initial={{ opacity: 0, x: reduce ? 0 : 16 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: reduce ? 0 : 12 }}
                transition={easeQuick}
                role={t.tone === 'error' ? 'alert' : 'status'}
                aria-live={t.tone === 'error' ? 'assertive' : 'polite'}
                className={`pointer-events-auto flex items-start gap-3 rounded-xl border p-3.5 shadow-md ${cls}`}
              >
                <Icon size={15} className={`mt-0.5 shrink-0 ${iconCls}`} aria-hidden="true" />
                <div className="min-w-0 flex-1">
                  <div className="text-xs font-medium text-slate-100">{t.title}</div>
                  {t.body ? (
                    <div className="mt-0.5 text-xs leading-relaxed text-slate-400 break-words">
                      {t.body}
                    </div>
                  ) : null}
                </div>
                <button
                  type="button"
                  onClick={() => dismiss(t.id)}
                  className="shrink-0 rounded p-0.5 text-slate-400 opacity-60 outline-none hover:opacity-100 hover:text-slate-200 transition-colors"
                  aria-label={`Dismiss: ${t.title}`}
                >
                  <X size={13} />
                </button>
              </m.div>
            );
          })}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  );
}

/** Small inline keyboard hint chip, styled as a physical keycap. */
export function Kbd({ children }: { children: ReactNode }) {
  return (
    <kbd className="tabular rounded-md border border-white/10 bg-abyss-800 px-1.5 py-0.5 text-[11px] font-mono text-slate-400 shadow-xs">
      {children}
    </kbd>
  );
}

export { easeQuick };
