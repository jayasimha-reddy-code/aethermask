import { useEffect, useRef } from 'react';
/**
 * AetherMask (CipherShift) :: Attestation drawer
 *
 * Surfaces `/api/v1/attestation` — the machine-checkable claim that this
 * deployment made zero external calls. Also reports the live browser-side
 * egress ledger recorded by `useEgressWatch`, so the operator sees BOTH the
 * server's self-report and an independent client-side observation.
 */

import { AnimatePresence, m } from 'motion/react';
import {
  Cpu,
  Globe,
  KeyRound,
  Library,
  Radio,
  ShieldCheck,
  X,
} from 'lucide-react';
import type { AttestationResponse } from '../lib/types';
import { formatInt } from '../lib/format';
import {
  backdropVariants,
  drawerVariants,
  listItemVariants,
  listVariants,
} from '../lib/motion';
import { Badge } from './ui/Primitives';

function Row({
  label,
  value,
  ok,
}: {
  label: string;
  value: string;
  ok?: boolean;
}) {
  return (
    <m.div
      variants={listItemVariants}
      className="flex items-center justify-between gap-4 border-b border-white/4 py-1.5 last:border-0"
    >
      <span className="text-xs text-slate-400">{label}</span>
      <span
        className={`tabular text-right text-xs ${
          ok === undefined
            ? 'text-slate-200'
            : ok
              ? 'text-signal-400'
              : 'text-classified-400'
        }`}
      >
        {value}
      </span>
    </m.div>
  );
}

function Section({
  icon,
  title,
  children,
}: {
  icon: React.ReactNode;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-xl border border-white/8 bg-abyss-850/60 p-4">
      <h3 className="mb-2 flex items-center gap-2 text-xs font-medium text-slate-200">
        <span className="text-slate-400" aria-hidden="true">
          {icon}
        </span>
        {title}
      </h3>
      <m.div variants={listVariants} initial="hidden" animate="visible">
        {children}
      </m.div>
    </section>
  );
}

export function AttestationDrawer({
  open,
  onClose,
  attestation,
  clientEgress,
}: {
  open: boolean;
  onClose: () => void;
  attestation: AttestationResponse | null;
  clientEgress: { total: number; external: string[] };
}) {
  const airgap = attestation?.airgap;
  const crypto = attestation?.cryptography as Record<string, unknown> | undefined;
  const lexicon = attestation?.lexicon;
  const nlp = attestation?.nlp as Record<string, unknown> | undefined;

  const panelRef = useRef<HTMLElement | null>(null);
  const restoreFocusRef = useRef<HTMLElement | null>(null);

  // Dialog keyboard contract: Escape dismisses, Tab is trapped inside the panel,
  // and focus returns to whatever opened the drawer. Without this the drawer is a
  // keyboard dead-end and its backdrop swallows every click behind it.
  useEffect(() => {
    if (!open) return;
    restoreFocusRef.current = document.activeElement as HTMLElement | null;

    const focusables = () =>
      Array.from(
        panelRef.current?.querySelectorAll<HTMLElement>(
          'a[href], button:not([disabled]), input:not([disabled]), select, textarea, [tabindex]:not([tabindex="-1"])',
        ) ?? [],
      ).filter((el) => el.offsetParent !== null || el === document.activeElement);

    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.stopPropagation();
        onClose();
        return;
      }
      if (e.key !== 'Tab') return;
      const items = focusables();
      if (items.length === 0) return;
      const first = items[0];
      const last = items[items.length - 1];
      const active = document.activeElement as HTMLElement | null;
      if (e.shiftKey && (active === first || !panelRef.current?.contains(active))) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && active === last) {
        e.preventDefault();
        first.focus();
      }
    };

    document.addEventListener('keydown', onKey, true);
    const raf = requestAnimationFrame(() => focusables()[0]?.focus());
    return () => {
      document.removeEventListener('keydown', onKey, true);
      cancelAnimationFrame(raf);
      restoreFocusRef.current?.focus?.();
    };
  }, [open, onClose]);

  return (
    <AnimatePresence>
      {open ? (
        <m.div
          className="fixed inset-0 z-50 flex justify-end"
          variants={backdropVariants}
          initial="hidden"
          animate="visible"
          exit="exit"
        >
          <div
            className="absolute inset-0 bg-abyss-950/75 backdrop-blur-sm"
            onClick={onClose}
            aria-hidden="true"
          />
          <m.aside
            role="dialog"
            aria-modal="true"
            aria-label="Air-gap attestation"
            ref={panelRef}
            className="relative z-10 flex h-full w-full max-w-md flex-col border-l border-abyss-700 bg-abyss-900"
            variants={drawerVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
          >
            <header className="flex items-center justify-between border-b border-abyss-700 px-5 py-4">
              <div className="flex items-center gap-2.5">
                <ShieldCheck size={17} className="text-signal-500" aria-hidden="true" />
                <div>
                  <h2 className="text-sm font-semibold text-slate-100">
                    Air-gap attestation
                  </h2>
                  <p className="text-[10.5px] text-slate-500">
                    {attestation?.product} v{attestation?.version}
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={onClose}
                className="rounded p-1 text-slate-400 outline-none hover:bg-abyss-800 hover:text-slate-100"
                aria-label="Close attestation"
              >
                <X size={16} />
              </button>
            </header>

            <div className="min-h-0 flex-1 space-y-3 overflow-auto p-5">
              {/* Client-observed egress: independent of anything the server says */}
              <Section icon={<Radio size={12} />} title="Browser-observed network">
                <Row
                  label="Total requests issued by this SPA"
                  value={formatInt(clientEgress.total)}
                />
                <Row
                  label="Requests to an external origin"
                  value={
                    clientEgress.external.length === 0
                      ? 'NONE'
                      : formatInt(clientEgress.external.length)
                  }
                  ok={clientEgress.external.length === 0}
                />
                {clientEgress.external.slice(0, 5).map((url) => (
                  <Row key={url} label="⚠ external" value={url} ok={false} />
                ))}
              </Section>

              {airgap ? (
                <Section icon={<Globe size={12} />} title="Server air-gap report">
                  <Row
                    label="Egress blocking active"
                    value={airgap.egress_blocking ? 'ENFORCED' : 'OFF'}
                    ok={airgap.egress_blocking}
                  />
                  <Row
                    label="Blocked egress attempts"
                    value={formatInt(airgap.blocked_attempts)}
                    ok={airgap.blocked_attempts === 0}
                  />
                  <Row label="External APIs" value={airgap.external_apis} ok />
                  <Row label="CDN assets" value={airgap.cdn_assets} ok />
                  <Row label="Telemetry" value={airgap.telemetry} ok />
                  <Row label="Model downloads" value={airgap.model_downloads} ok />
                </Section>
              ) : null}

              {crypto ? (
                <Section icon={<KeyRound size={12} />} title="Cryptography">
                  {Object.entries(crypto)
                    .filter(([, v]) => typeof v !== 'object')
                    .map(([k, v]) => (
                      <Row key={k} label={k.replace(/_/g, ' ')} value={String(v)} />
                    ))}
                </Section>
              ) : null}

              {lexicon ? (
                <Section icon={<Library size={12} />} title="Offline lexicon capacity">
                  <Row
                    label="Cover domain profiles"
                    value={formatInt(lexicon.profiles)}
                  />
                  <Row
                    label="Unique surrogate values"
                    value={formatInt(lexicon.total_unique_surrogates)}
                  />
                  <Row
                    label="Token shift rules"
                    value={formatInt(lexicon.total_token_shift_rules)}
                  />
                  <Row
                    label="Sensitivity rules"
                    value={formatInt(lexicon.sensitivity_rules)}
                  />
                  <Row label="NER patterns" value={formatInt(lexicon.ner_patterns)} />
                </Section>
              ) : null}

              {nlp ? (
                <Section icon={<Cpu size={12} />} title="Offline NLP engine">
                  {Object.entries(nlp)
                    .filter(([, v]) => typeof v !== 'object')
                    .map(([k, v]) => (
                      <Row key={k} label={k.replace(/_/g, ' ')} value={String(v)} />
                    ))}
                </Section>
              ) : null}

              {attestation?.supported_formats ? (
                <section className="rounded-xl border border-white/8 bg-abyss-850/60 p-4">
                  <h3 className="mb-2 text-xs font-medium text-slate-200">
                    Supported formats
                  </h3>
                  <div className="flex flex-wrap gap-1.5">
                    {attestation.supported_formats.map((f) => (
                      <Badge key={f} tone="muted">
                        {f}
                      </Badge>
                    ))}
                  </div>
                </section>
              ) : null}
            </div>
          </m.aside>
        </m.div>
      ) : null}
    </AnimatePresence>
  );
}
