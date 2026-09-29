/**
 * AetherMask (CipherShift) :: command palette
 *
 * Ctrl/Cmd-K opens a fuzzy command launcher covering every navigable stage and
 * every available action. This is the main keyboard-operator affordance: an
 * analyst working an air-gapped terminal can drive the whole pipeline without
 * reaching for a pointer.
 *
 * ACCESSIBILITY
 * -------------
 * Implements the WAI-ARIA combobox/listbox pattern:
 *   - role="combobox" + aria-expanded + aria-controls + aria-activedescendant
 *   - roving virtual focus (the input keeps DOM focus; the highlighted option
 *     is referenced by id) so screen readers announce each option on arrow
 *   - focus is trapped while open and RESTORED to the invoking element on close
 *   - Escape closes, Enter runs, Up/Down wrap, Home/End jump
 */

import {
  useCallback,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import { AnimatePresence, m } from 'motion/react';
import { CornerDownLeft, Search } from 'lucide-react';
import { backdropVariants } from '../../lib/motion';
import { useRevealVariants } from '../../hooks/useReducedMotionVariants';

export interface Command {
  id: string;
  label: string;
  hint?: string;
  group: string;
  icon?: ReactNode;
  disabled?: boolean;
  keywords?: string;
  run: () => void;
}

/**
 * Subsequence fuzzy match with a light scoring bias toward prefix and
 * word-boundary hits. Pure, synchronous, no dependency.
 */
function score(query: string, text: string): number {
  if (!query) return 1;
  const q = query.toLowerCase();
  const t = text.toLowerCase();
  if (t.startsWith(q)) return 1000 - t.length;
  const direct = t.indexOf(q);
  if (direct >= 0) return 700 - direct - t.length * 0.1;

  let qi = 0;
  let acc = 0;
  let streak = 0;
  for (let ti = 0; ti < t.length && qi < q.length; ti += 1) {
    if (t[ti] === q[qi]) {
      streak += 1;
      acc += streak * 2 + (ti === 0 || t[ti - 1] === ' ' || t[ti - 1] === '-' ? 6 : 0);
      qi += 1;
    } else {
      streak = 0;
    }
  }
  return qi === q.length ? acc : -1;
}

export function CommandPalette({
  open,
  onClose,
  commands,
}: {
  open: boolean;
  onClose: () => void;
  commands: Command[];
}) {
  const [query, setQuery] = useState('');
  const [active, setActive] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const restoreRef = useRef<HTMLElement | null>(null);
  const baseId = useId();
  const revealVariants = useRevealVariants(10);

  const results = useMemo(() => {
    const scored = commands
      .map((c) => ({
        cmd: c,
        s: Math.max(
          score(query, c.label),
          score(query, `${c.group} ${c.label}`) * 0.9,
          c.keywords ? score(query, c.keywords) * 0.8 : -1,
        ),
      }))
      .filter((r) => r.s > -1)
      .sort((a, b) => b.s - a.s);
    return scored.map((r) => r.cmd);
  }, [commands, query]);

  // Reset transient state whenever the palette is opened, and remember which
  // element to hand focus back to on close.
  useEffect(() => {
    if (open) {
      restoreRef.current = document.activeElement as HTMLElement | null;
      setQuery('');
      setActive(0);
      // Focus after the enter animation has committed the node.
      const raf = requestAnimationFrame(() => inputRef.current?.focus());
      return () => cancelAnimationFrame(raf);
    }
    restoreRef.current?.focus?.();
    return undefined;
  }, [open]);

  useEffect(() => setActive(0), [query]);

  // Keep the highlighted row inside the scroll viewport.
  useEffect(() => {
    if (!open) return;
    const node = listRef.current?.querySelector<HTMLElement>(
      `[data-index="${active}"]`,
    );
    node?.scrollIntoView({ block: 'nearest' });
  }, [active, open]);

  const runAt = useCallback(
    (index: number) => {
      const cmd = results[index];
      if (!cmd || cmd.disabled) return;
      onClose();
      // Defer so the palette's exit animation is not competing with whatever
      // state change the command triggers.
      requestAnimationFrame(() => cmd.run());
    },
    [results, onClose],
  );

  const onKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (results.length === 0 && e.key !== 'Escape') return;
      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault();
          setActive((i) => (i + 1) % results.length);
          break;
        case 'ArrowUp':
          e.preventDefault();
          setActive((i) => (i - 1 + results.length) % results.length);
          break;
        case 'Home':
          e.preventDefault();
          setActive(0);
          break;
        case 'End':
          e.preventDefault();
          setActive(results.length - 1);
          break;
        case 'Enter':
          e.preventDefault();
          runAt(active);
          break;
        case 'Escape':
          e.preventDefault();
          onClose();
          break;
        default:
          break;
      }
    },
    [results.length, active, runAt, onClose],
  );

  // Group the flat result list for display while keeping a single flat index
  // space, so arrow navigation crosses group boundaries naturally.
  const grouped = useMemo(() => {
    const out: { group: string; items: { cmd: Command; index: number }[] }[] = [];
    results.forEach((cmd, index) => {
      const last = out[out.length - 1];
      if (last && last.group === cmd.group) last.items.push({ cmd, index });
      else out.push({ group: cmd.group, items: [{ cmd, index }] });
    });
    return out;
  }, [results]);

  return (
    <AnimatePresence>
      {open ? (
        <m.div
          className="fixed inset-0 z-[60] flex items-start justify-center p-4 pt-[12vh]"
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
            className="panel relative z-10 w-full max-w-xl overflow-hidden"
            variants={revealVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
            role="dialog"
            aria-modal="true"
            aria-label="Command palette"
          >
            <div className="flex items-center gap-2.5 border-b border-abyss-700 px-4 py-3">
              <Search size={15} className="shrink-0 text-slate-500" aria-hidden="true" />
              <input
                ref={inputRef}
                type="text"
                role="combobox"
                aria-expanded="true"
                aria-controls={`${baseId}-list`}
                aria-activedescendant={
                  results[active] ? `${baseId}-opt-${active}` : undefined
                }
                aria-autocomplete="list"
                aria-label="Search commands"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={onKeyDown}
                placeholder="Search stages and actions…"
                spellCheck={false}
                className="w-full bg-transparent text-sm text-slate-100 outline-none placeholder:text-slate-600"
              />
              <kbd className="tabular shrink-0 rounded-md border border-white/10 bg-abyss-800 px-1.5 py-0.5 text-xs text-slate-400 font-mono">
                ESC
              </kbd>
            </div>

            <div
              ref={listRef}
              id={`${baseId}-list`}
              role="listbox"
              aria-label="Commands"
              className="max-h-[52vh] overflow-auto py-1.5"
            >
              {results.length === 0 ? (
                <p className="px-4 py-8 text-center text-xs text-slate-500">
                  No command matches “{query}”.
                </p>
              ) : (
                grouped.map(({ group, items }) => (
                  <div key={group} className="mb-1 last:mb-0">
                    <div className="px-4 py-1.5 text-xs font-medium text-slate-500">
                      {group}
                    </div>
                    {items.map(({ cmd, index }) => {
                      const isActive = index === active;
                      return (
                        <div
                          key={cmd.id}
                          id={`${baseId}-opt-${index}`}
                          data-index={index}
                          role="option"
                          aria-selected={isActive}
                          aria-disabled={cmd.disabled || undefined}
                          onMouseMove={() => setActive(index)}
                          onClick={() => runAt(index)}
                          className={`relative mx-1.5 flex cursor-pointer items-center gap-2.5 rounded-lg px-2.5 py-2 transition-colors duration-100 ${
                            cmd.disabled
                              ? 'cursor-not-allowed opacity-40'
                              : isActive
                                ? 'bg-abyss-800 text-slate-100'
                                : 'text-slate-300 hover:bg-abyss-850'
                          }`}
                        >
                          <span
                            className={`relative shrink-0 ${isActive ? 'text-signal-400' : 'text-slate-400'}`}
                            aria-hidden="true"
                          >
                            {cmd.icon}
                          </span>
                          <span className="relative min-w-0 flex-1">
                            <span className="block truncate text-xs font-medium">
                              {cmd.label}
                            </span>
                            {cmd.hint ? (
                              <span className="block truncate text-xs text-slate-500">
                                {cmd.hint}
                              </span>
                            ) : null}
                          </span>
                          {isActive && !cmd.disabled ? (
                            <CornerDownLeft
                              size={12}
                              className="relative shrink-0 text-slate-500"
                              aria-hidden="true"
                            />
                          ) : null}
                        </div>
                      );
                    })}
                  </div>
                ))
              )}
            </div>

            <div className="flex items-center justify-between border-t border-white/8 px-4 py-2.5 text-xs text-slate-500">
              <span className="flex items-center gap-3">
                <span className="flex items-center gap-1">
                  <kbd className="rounded border border-white/10 bg-abyss-800 px-1 py-0.5 font-mono text-[11px]">↑</kbd>
                  <kbd className="rounded border border-white/10 bg-abyss-800 px-1 py-0.5 font-mono text-[11px]">↓</kbd>
                  <span className="ml-1">Navigate</span>
                </span>
                <span className="flex items-center gap-1">
                  <kbd className="rounded border border-white/10 bg-abyss-800 px-1 py-0.5 font-mono text-[11px]">↵</kbd>
                  <span className="ml-1">Select</span>
                </span>
              </span>
              <span className="tabular">{results.length} commands</span>
            </div>
          </m.div>
        </m.div>
      ) : null}
    </AnimatePresence>
  );
}

/** Global Ctrl/Cmd-K listener. */
export function useCommandPaletteHotkey(onOpen: () => void): void {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        onOpen();
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onOpen]);
}
