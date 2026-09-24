/**
 * AetherMask (CipherShift) :: shared UI primitives
 *
 * Craftsmen building blocks for the offline air-gapped studio.
 * Quiet chrome, restrained palette, nested radii, and 4px-grid alignment.
 */

import { AnimatePresence, m } from 'motion/react';
import type { ReactNode } from 'react';
import { useEffect, useId, useRef, useState } from 'react';
import {
  AlertTriangle,
  Check,
  Copy,
  Info,
  Loader2,
  ShieldAlert,
  X,
} from 'lucide-react';
import {
  backdropVariants,
  easeQuick,
  fadeVariants,
  panelVariants,
  pressable,
  verdictVariants,
} from '../../lib/motion';
import { copyText } from '../../lib/format';

/* -------------------------------------------------------------------------- */
/*  Panel                                                                      */
/* -------------------------------------------------------------------------- */

export function Panel({
  children,
  className = '',
  as: Tag = 'section',
}: {
  children: ReactNode;
  className?: string;
  as?: 'section' | 'div' | 'aside';
}) {
  return <Tag className={`panel ${className}`}>{children}</Tag>;
}

export function PanelHeader({
  icon,
  title,
  subtitle,
  actions,
}: {
  icon?: ReactNode;
  title: string;
  subtitle?: string;
  actions?: ReactNode;
}) {
  return (
    <header className="flex items-start justify-between gap-4 border-b border-white/8 px-5 py-4">
      <div className="flex min-w-0 items-start gap-3">
        {icon ? (
          <span className="mt-0.5 shrink-0 text-slate-400" aria-hidden="true">
            {icon}
          </span>
        ) : null}
        <div className="min-w-0">
          <h2 className="truncate text-sm font-medium text-slate-100">
            {title}
          </h2>
          {subtitle ? (
            <p className="mt-0.5 text-xs leading-relaxed text-slate-400">
              {subtitle}
            </p>
          ) : null}
        </div>
      </div>
      {actions ? <div className="shrink-0">{actions}</div> : null}
    </header>
  );
}

/* -------------------------------------------------------------------------- */
/*  Button                                                                     */
/* -------------------------------------------------------------------------- */

type ButtonTone = 'primary' | 'vault' | 'ghost' | 'danger' | 'neutral';

const TONE_CLASS: Record<ButtonTone, string> = {
  primary:
    'bg-slate-100 text-abyss-950 hover:bg-white active:bg-slate-200 font-medium shadow-sm',
  vault:
    'bg-abyss-800 text-slate-100 hover:bg-abyss-750 active:bg-abyss-700 border border-white/8 font-medium',
  danger:
    'bg-classified-600/90 text-white hover:bg-classified-600 active:bg-classified-700 font-medium',
  neutral:
    'bg-abyss-800 text-slate-200 hover:bg-abyss-750 active:bg-abyss-700 border border-white/8 font-medium',
  ghost:
    'bg-transparent text-slate-400 hover:bg-abyss-800 hover:text-slate-200 disabled:text-slate-600 font-medium',
};

export function Button({
  children,
  onClick,
  tone = 'neutral',
  disabled = false,
  busy = false,
  type = 'button',
  className = '',
  title,
  icon,
}: {
  children: ReactNode;
  onClick?: () => void;
  tone?: ButtonTone;
  disabled?: boolean;
  busy?: boolean;
  type?: 'button' | 'submit';
  className?: string;
  title?: string;
  icon?: ReactNode;
}) {
  const inert = disabled || busy;
  return (
    <m.button
      type={type}
      onClick={onClick}
      disabled={inert}
      title={title}
      aria-busy={busy || undefined}
      className={`inline-flex h-9 items-center justify-center gap-2 rounded-lg px-3.5 text-xs outline-none transition-colors duration-150 ${TONE_CLASS[tone]} ${inert ? 'cursor-not-allowed opacity-40' : 'cursor-pointer'} ${className}`}
      whileTap={inert ? undefined : pressable.whileTap}
      transition={easeQuick}
    >
      {busy ? (
        <Loader2 size={14} className="animate-spin" aria-hidden="true" />
      ) : (
        icon
      )}
      {children}
    </m.button>
  );
}

/* -------------------------------------------------------------------------- */
/*  Badge / Chip (nested 6px radius, no pills)                                 */
/* -------------------------------------------------------------------------- */

type BadgeTone =
  | 'signal'
  | 'classified'
  | 'vault'
  | 'caution'
  | 'neutral'
  | 'muted';

const BADGE_CLASS: Record<BadgeTone, string> = {
  signal: 'bg-signal-500/10 text-signal-400 border border-signal-500/20',
  classified: 'bg-classified-500/10 text-classified-400 border border-classified-500/20',
  vault: 'bg-vault-500/10 text-vault-400 border border-vault-500/20',
  caution: 'bg-caution-500/10 text-caution-400 border border-caution-500/20',
  neutral: 'bg-abyss-800 text-slate-200 border border-white/8',
  muted: 'bg-abyss-850 text-slate-400 border border-white/6',
};

export function Badge({
  children,
  tone = 'neutral',
  className = '',
  title,
}: {
  children: ReactNode;
  tone?: BadgeTone;
  className?: string;
  title?: string;
}) {
  return (
    <span
      title={title}
      className={`inline-flex items-center gap-1.5 rounded-md px-2 py-0.5 text-xs font-normal ${BADGE_CLASS[tone]} ${className}`}
    >
      {children}
    </span>
  );
}

/* -------------------------------------------------------------------------- */
/*  Stat tile                                                                  */
/* -------------------------------------------------------------------------- */

export function Stat({
  label,
  value,
  hint,
  tone = 'neutral',
  icon,
}: {
  label: string;
  value: ReactNode;
  hint?: string;
  tone?: BadgeTone;
  icon?: ReactNode;
}) {
  const valueColor =
    tone === 'classified'
      ? 'text-classified-400'
      : tone === 'signal'
        ? 'text-signal-400'
        : 'text-slate-100';

  return (
    <div className="rounded-xl border border-white/8 bg-abyss-850/60 p-4">
      <div className="flex items-center gap-1.5 text-xs font-normal text-slate-400">
        {icon ? <span className="text-slate-500" aria-hidden="true">{icon}</span> : null}
        {label}
      </div>
      <div className={`tabular mt-2 text-2xl font-normal leading-none ${valueColor}`}>
        {value}
      </div>
      {hint ? <div className="mt-1.5 text-xs text-slate-500">{hint}</div> : null}
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/*  Copyable value                                                             */
/* -------------------------------------------------------------------------- */

export function Copyable({
  value,
  display,
  className = '',
}: {
  value: string;
  display?: string;
  className?: string;
}) {
  const [done, setDone] = useState(false);
  const timer = useRef<number | undefined>(undefined);

  useEffect(() => () => window.clearTimeout(timer.current), []);

  return (
    <m.button
      type="button"
      onClick={() => {
        void copyText(value).then((ok) => {
          if (!ok) return;
          setDone(true);
          window.clearTimeout(timer.current);
          timer.current = window.setTimeout(() => setDone(false), 1600);
        });
      }}
      title={`Copy: ${value}`}
      className={`tabular group inline-flex items-center gap-1.5 rounded-md border border-white/8 bg-abyss-800/80 px-2.5 py-1 text-xs text-slate-300 outline-none hover:border-white/16 hover:text-slate-100 ${className}`}
      whileTap={pressable.whileTap}
      transition={easeQuick}
    >
      <span className="truncate">{display ?? value}</span>
      <AnimatePresence mode="wait" initial={false}>
        {done ? (
          <m.span
            key="done"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={easeQuick}
            className="text-signal-400"
          >
            <Check size={13} aria-label="Copied" />
          </m.span>
        ) : (
          <m.span
            key="copy"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={easeQuick}
            className="text-slate-500 group-hover:text-slate-300"
          >
            <Copy size={13} aria-hidden="true" />
          </m.span>
        )}
      </AnimatePresence>
    </m.button>
  );
}

/* -------------------------------------------------------------------------- */
/*  Alert                                                                      */
/* -------------------------------------------------------------------------- */

export function Alert({
  tone,
  title,
  children,
  onDismiss,
}: {
  tone: 'error' | 'warning' | 'info' | 'success';
  title: string;
  children?: ReactNode;
  onDismiss?: () => void;
}) {
  const config = {
    error: {
      cls: 'border-classified-600/30 bg-classified-600/10 text-classified-400',
      Icon: ShieldAlert,
    },
    warning: {
      cls: 'border-caution-500/30 bg-caution-500/10 text-caution-400',
      Icon: AlertTriangle,
    },
    info: {
      cls: 'border-white/8 bg-abyss-800/80 text-slate-300',
      Icon: Info,
    },
    success: {
      cls: 'border-signal-600/30 bg-signal-600/10 text-signal-400',
      Icon: Check,
    },
  }[tone];
  const { Icon } = config;

  return (
    <m.div
      role={tone === 'error' ? 'alert' : 'status'}
      variants={verdictVariants}
      initial="hidden"
      animate="visible"
      exit="hidden"
      className={`flex items-start gap-3 rounded-xl border p-4 ${config.cls}`}
    >
      <Icon size={16} className="mt-0.5 shrink-0" aria-hidden="true" />
      <div className="min-w-0 flex-1">
        <div className="text-xs font-medium text-slate-100">{title}</div>
        {children ? (
          <div className="mt-1 text-xs leading-relaxed break-words opacity-90">
            {children}
          </div>
        ) : null}
      </div>
      {onDismiss ? (
        <button
          type="button"
          onClick={onDismiss}
          className="shrink-0 rounded p-1 text-slate-400 opacity-60 outline-none hover:opacity-100 hover:text-slate-200"
          aria-label="Dismiss"
        >
          <X size={14} />
        </button>
      ) : null}
    </m.div>
  );
}

/* -------------------------------------------------------------------------- */
/*  Field wrapper (sentence case labels, 4px grid)                            */
/* -------------------------------------------------------------------------- */

export function Field({
  label,
  hint,
  children,
  htmlFor,
}: {
  label: string;
  hint?: string;
  children: ReactNode;
  htmlFor?: string;
}) {
  return (
    <div className="space-y-1.5">
      <label
        htmlFor={htmlFor}
        className="block text-xs font-medium text-slate-300"
      >
        {label}
      </label>
      {children}
      {hint ? <p className="text-xs text-slate-500">{hint}</p> : null}
    </div>
  );
}

export const inputClass =
  'w-full rounded-lg border border-white/8 bg-abyss-900 px-3 py-2 text-xs text-slate-100 outline-none placeholder:text-slate-600 focus:border-signal-500 focus:ring-1 focus:ring-signal-500/30 transition-colors';

/* -------------------------------------------------------------------------- */
/*  Progress bar                                                               */
/* -------------------------------------------------------------------------- */

export function MeterBar({
  value,
  max = 1,
  tone = 'signal',
  className = '',
  label,
}: {
  value: number;
  max?: number;
  tone?: 'signal' | 'classified' | 'vault' | 'caution';
  className?: string;
  label?: string;
}) {
  const pct = max > 0 ? Math.max(0, Math.min(1, value / max)) : 0;
  const bar: Record<string, string> = {
    signal: 'bg-signal-500',
    classified: 'bg-classified-500',
    vault: 'bg-vault-500',
    caution: 'bg-caution-500',
  };
  return (
    <div
      className={`h-1.5 w-full overflow-hidden rounded-md bg-abyss-800 ${className}`}
      role="progressbar"
      aria-valuenow={Math.round(pct * 100)}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label={label}
    >
      <div
        className={`h-full rounded-md transition-all duration-200 ${bar[tone]}`}
        style={{ width: `${Math.round(pct * 100)}%` }}
      />
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/*  Modal                                                                      */
/* -------------------------------------------------------------------------- */

export function Modal({
  open,
  onClose,
  title,
  children,
  width = 'max-w-2xl',
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  width?: string;
}) {
  const titleId = useId();

  useEffect(() => {
    if (!open) return undefined;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      window.removeEventListener('keydown', onKey);
      document.body.style.overflow = prev;
    };
  }, [open, onClose]);

  return (
    <AnimatePresence>
      {open ? (
        <m.div
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
          variants={backdropVariants}
          initial="hidden"
          animate="visible"
          exit="exit"
        >
          <div
            className="absolute inset-0 bg-abyss-950/80 backdrop-blur-sm"
            onClick={onClose}
            aria-hidden="true"
          />
          <m.div
            role="dialog"
            aria-modal="true"
            aria-labelledby={titleId}
            className={`panel relative z-10 max-h-[85vh] w-full ${width} overflow-hidden`}
            variants={panelVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
          >
            <div className="flex items-center justify-between border-b border-white/8 px-5 py-4">
              <h2 id={titleId} className="text-sm font-medium text-slate-100">
                {title}
              </h2>
              <button
                type="button"
                onClick={onClose}
                className="rounded p-1 text-slate-400 outline-none hover:bg-abyss-800 hover:text-slate-100"
                aria-label="Close dialog"
              >
                <X size={16} />
              </button>
            </div>
            <div className="max-h-[calc(85vh-3.5rem)] overflow-auto p-5">
              {children}
            </div>
          </m.div>
        </m.div>
      ) : null}
    </AnimatePresence>
  );
}

/* -------------------------------------------------------------------------- */
/*  Empty state                                                                */
/* -------------------------------------------------------------------------- */

export function EmptyState({
  icon,
  title,
  children,
}: {
  icon: ReactNode;
  title: string;
  children?: ReactNode;
}) {
  return (
    <m.div
      variants={fadeVariants}
      initial="hidden"
      animate="visible"
      className="flex flex-col items-center justify-center gap-3 px-6 py-12 text-center"
    >
      <div className="rounded-xl border border-white/8 bg-abyss-850 p-3 text-slate-400">
        {icon}
      </div>
      <div className="text-sm font-medium text-slate-200">{title}</div>
      {children ? (
        <div className="max-w-md text-xs leading-relaxed text-slate-500">
          {children}
        </div>
      ) : null}
    </m.div>
  );
}
