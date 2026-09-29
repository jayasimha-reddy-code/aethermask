/**
 * AetherMask (CipherShift) :: interactive controls
 *
 * DropZone, PassphraseField, ProfilePicker and NumericModeToggle.
 * Quiet chrome, 4px grid rhythm, restrained palette.
 */

import { useCallback, useId, useMemo, useRef, useState } from 'react';
import { AnimatePresence, m } from 'motion/react';
import {
  Check,
  Eye,
  EyeOff,
  FileSpreadsheet,
  FileText,
  Hash,
  Lock,
  Sigma,
  Upload,
  X,
} from 'lucide-react';
import type { DomainProfileInfo, NumericMode } from '../../lib/types';
import { formatBytes, formatInt, passphraseStrength } from '../../lib/format';
import {
  fadeVariants,
  revealVariants,
} from '../../lib/motion';
import { Badge, Field, MeterBar, inputClass } from '../ui/Primitives';

/* -------------------------------------------------------------------------- */
/*  DropZone                                                                   */
/* -------------------------------------------------------------------------- */

export function DropZone({
  file,
  onFile,
  accept,
  label,
  hint,
  compact = false,
}: {
  file: File | null;
  onFile: (f: File | null) => void;
  accept: string;
  label: string;
  hint?: string;
  tone?: 'signal' | 'vault';
  compact?: boolean;
}) {
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const inputId = useId();

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      const dropped = e.dataTransfer.files?.[0];
      if (dropped) onFile(dropped);
    },
    [onFile],
  );

  return (
    <div>
      <input
        ref={inputRef}
        id={inputId}
        type="file"
        accept={accept}
        className="sr-only"
        onChange={(e) => onFile(e.target.files?.[0] ?? null)}
      />
      <label
        htmlFor={inputId}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        className={`relative flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border border-dashed text-center outline-none transition-colors duration-150 ${
          compact ? 'p-4' : 'p-6'
        } ${
          dragging
            ? 'border-signal-500 bg-signal-500/10'
            : file
              ? 'border-white/12 bg-abyss-850/80'
              : 'border-white/8 bg-abyss-900/50 hover:border-white/16 hover:bg-abyss-850/50'
        }`}
      >
        <AnimatePresence mode="wait" initial={false}>
          {file ? (
            <m.div
              key="has-file"
              variants={revealVariants}
              initial="hidden"
              animate="visible"
              exit="exit"
              className="flex w-full items-center gap-3"
            >
              <span className="shrink-0 text-slate-400" aria-hidden="true">
                {/\.(xlsx|xls)$/i.test(file.name) ? (
                  <FileSpreadsheet size={18} />
                ) : (
                  <FileText size={18} />
                )}
              </span>
              <span className="min-w-0 flex-1 text-left">
                <span className="tabular block truncate text-xs font-medium text-slate-200">
                  {file.name}
                </span>
                <span className="block text-xs text-slate-500">
                  {formatBytes(file.size)}
                  {file.type ? ` · ${file.type}` : ''}
                </span>
              </span>
              <button
                type="button"
                onClick={(e) => {
                  e.preventDefault();
                  onFile(null);
                  if (inputRef.current) inputRef.current.value = '';
                }}
                className="shrink-0 rounded p-1 text-slate-400 outline-none hover:bg-abyss-750 hover:text-slate-200 transition-colors"
                aria-label={`Remove ${file.name}`}
              >
                <X size={14} />
              </button>
            </m.div>
          ) : (
            <m.div
              key="empty"
              variants={fadeVariants}
              initial="hidden"
              animate="visible"
              exit="exit"
              className="flex flex-col items-center gap-2"
            >
              <span
                className={`transition-colors ${dragging ? 'text-signal-400' : 'text-slate-500'}`}
                aria-hidden="true"
              >
                <Upload size={compact ? 16 : 20} />
              </span>
              <span className="text-xs font-medium text-slate-300">{label}</span>
              {hint ? (
                <span className="text-xs text-slate-500">{hint}</span>
              ) : null}
            </m.div>
          )}
        </AnimatePresence>
      </label>
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/*  PassphraseField                                                            */
/* -------------------------------------------------------------------------- */

export function PassphraseField({
  value,
  onChange,
  label = 'Vault passphrase',
  hint,
  showStrength = true,
  autoComplete = 'new-password',
}: {
  value: string;
  onChange: (v: string) => void;
  label?: string;
  hint?: string;
  showStrength?: boolean;
  autoComplete?: string;
}) {
  const [visible, setVisible] = useState(false);
  const id = useId();
  const strength = useMemo(() => passphraseStrength(value), [value]);

  const TONE = ['classified', 'classified', 'caution', 'signal', 'signal'] as const;
  const tone = TONE[strength.score];

  return (
    <Field
      label={label}
      htmlFor={id}
      hint={hint ?? 'Argon2id · processed exclusively in local memory'}
    >
      <div className="relative">
        <Lock
          size={14}
          className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-slate-500"
          aria-hidden="true"
        />
        <input
          id={id}
          type={visible ? 'text' : 'password'}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          autoComplete={autoComplete}
          spellCheck={false}
          placeholder="Minimum 8 characters"
          aria-describedby={showStrength ? `${id}-strength` : undefined}
          className={`${inputClass} px-9`}
        />
        <button
          type="button"
          onClick={() => setVisible((v) => !v)}
          className="absolute top-1/2 right-2.5 -translate-y-1/2 rounded p-1 text-slate-400 outline-none hover:text-slate-200 transition-colors"
          aria-label={visible ? 'Hide passphrase' : 'Show passphrase'}
          aria-pressed={visible}
        >
          {visible ? <EyeOff size={14} /> : <Eye size={14} />}
        </button>
      </div>

      {showStrength && value ? (
        <m.div
          id={`${id}-strength`}
          variants={revealVariants}
          initial="hidden"
          animate="visible"
          className="space-y-1 pt-1"
        >
          <MeterBar
            value={strength.score}
            max={4}
            tone={tone}
            label={`Passphrase strength: ${strength.label}`}
          />
          <div className="flex items-center justify-between gap-2 text-xs">
            <span
              className={
                strength.score >= 3
                  ? 'text-signal-400'
                  : strength.score === 2
                    ? 'text-caution-400'
                    : 'text-classified-400'
              }
            >
              {strength.label}
            </span>
            <span className="text-slate-500">{strength.hint}</span>
          </div>
        </m.div>
      ) : null}
    </Field>
  );
}

/* -------------------------------------------------------------------------- */
/*  ProfilePicker                                                              */
/* -------------------------------------------------------------------------- */

export function ProfilePicker({
  profiles,
  selected,
  onSelect,
  recommended,
}: {
  profiles: DomainProfileInfo[];
  selected: string;
  onSelect: (key: string) => void;
  recommended?: string;
}) {
  return (
    <ul
      className="grid gap-3 sm:grid-cols-2"
      role="radiogroup"
      aria-label="Domain shift profile"
    >
      {profiles.map((profile) => {
        const active = profile.key === selected;
        const isRecommended = profile.key === recommended;
        return (
          <li key={profile.key}>
            <button
              type="button"
              role="radio"
              aria-checked={active}
              onClick={() => onSelect(profile.key)}
              className={`relative h-full w-full rounded-xl border p-4 text-left outline-none transition-colors duration-150 ${
                active
                  ? 'border-signal-500/40 bg-signal-500/5'
                  : 'border-white/8 bg-abyss-850/60 hover:border-white/16 hover:bg-abyss-800/60'
              }`}
            >
              <div className="flex items-start justify-between gap-2">
                <span
                  className={`text-xs font-medium ${active ? 'text-signal-400' : 'text-slate-200'}`}
                >
                  {profile.title}
                </span>
                {active ? (
                  <span className="shrink-0 text-signal-400" aria-hidden="true">
                    <Check size={14} />
                  </span>
                ) : null}
              </div>

              <p className="mt-1.5 line-clamp-2 text-xs leading-relaxed text-slate-400">
                {profile.description}
              </p>

              <div className="mt-3 flex flex-wrap gap-1.5">
                <Badge tone="muted">{profile.token_rules} token rules</Badge>
                {profile.pool_capacity ? (
                  <Badge tone="muted">
                    {formatInt(Number(profile.pool_capacity))} surrogates
                  </Badge>
                ) : null}
                {isRecommended ? (
                  <Badge tone="signal">Recommended</Badge>
                ) : null}
              </div>
            </button>
          </li>
        );
      })}
    </ul>
  );
}

/* -------------------------------------------------------------------------- */
/*  NumericModeToggle                                                          */
/* -------------------------------------------------------------------------- */

export function NumericModeToggle({
  mode,
  onChange,
}: {
  mode: NumericMode;
  onChange: (m: NumericMode) => void;
}) {
  const OPTIONS = [
    {
      id: 'identity' as const,
      label: 'Leave untouched',
      Icon: Hash,
      blurb:
        'Numerics and coordinates pass through byte-identical. Every aggregate is bit-exact.',
    },
    {
      id: 'affine' as const,
      label: 'Reversible affine y = ax + b',
      Icon: Sigma,
      blurb:
        'Scales and shifts numerics. Correlations and trends survive; exact magnitudes stay masked until restore.',
    },
  ];

  return (
    <div
      className="grid gap-3 sm:grid-cols-2"
      role="radiogroup"
      aria-label="Numeric handling mode"
    >
      {OPTIONS.map(({ id, label, Icon, blurb }) => {
        const active = mode === id;
        return (
          <button
            key={id}
            type="button"
            role="radio"
            aria-checked={active}
            onClick={() => onChange(id)}
            className={`rounded-xl border p-4 text-left outline-none transition-colors duration-150 ${
              active
                ? 'border-signal-500/40 bg-signal-500/5'
                : 'border-white/8 bg-abyss-850/60 hover:border-white/16 hover:bg-abyss-800/60'
            }`}
          >
            <div className="flex items-center gap-2">
              <Icon
                size={14}
                className={active ? 'text-signal-400' : 'text-slate-400'}
                aria-hidden="true"
              />
              <span
                className={`text-xs font-medium ${active ? 'text-signal-400' : 'text-slate-200'}`}
              >
                {label}
              </span>
            </div>
            <p className="mt-1.5 text-xs leading-relaxed text-slate-400">
              {blurb}
            </p>
          </button>
        );
      })}
    </div>
  );
}
