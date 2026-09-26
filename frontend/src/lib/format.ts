/**
 * AetherMask (CipherShift) :: pure formatting helpers
 *
 * No dependencies, no locale downloads, no network. Uses Intl only where the
 * runtime already provides the data locally.
 */

const BYTES_PER_KB = 1024;
const COMPACT_THRESHOLD = 1000;
const DASH_PLACEHOLDER = '-';

/** Human-readable byte size. */
export function formatBytes(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes < 0) return DASH_PLACEHOLDER;
  if (bytes < BYTES_PER_KB) return `${bytes} B`;
  const units = ['KB', 'MB', 'GB', 'TB'];
  let value = bytes / BYTES_PER_KB;
  let unit = 0;
  while (value >= BYTES_PER_KB && unit < units.length - 1) {
    value /= BYTES_PER_KB;
    unit += 1;
  }
  return `${value.toFixed(value >= 100 ? 0 : 1)} ${units[unit]}`;
}

/** Thousands-separated integer. */
export function formatInt(n: number | null | undefined): string {
  if (n === null || n === undefined || !Number.isFinite(n)) return DASH_PLACEHOLDER;
  return n.toLocaleString('en-US');
}

/** Compact number for dense chips (1.2k, 3.4M). */
export function formatCompact(n: number | null | undefined): string {
  if (n === null || n === undefined || !Number.isFinite(n)) return DASH_PLACEHOLDER;
  if (Math.abs(n) < COMPACT_THRESHOLD) return String(n);
  return new Intl.NumberFormat('en-US', {
    notation: 'compact',
    maximumFractionDigits: 1,
  }).format(n);
}

/** Percentage with a single decimal. */
export function formatPct(ratio: number | null | undefined): string {
  if (ratio === null || ratio === undefined || !Number.isFinite(ratio)) return DASH_PLACEHOLDER;
  return `${(ratio * 100).toFixed(1)}%`;
}

/** Render any cell value for display without throwing on odd types. */
export function displayCell(
  value: string | number | boolean | null | undefined,
): string {
  if (value === null || value === undefined) return '∅';
  if (typeof value === 'boolean') return value ? 'true' : 'false';
  if (typeof value === 'number') {
    return Number.isInteger(value) ? String(value) : String(value);
  }
  return String(value);
}

/** Abbreviate a long hash for inline display, keeping head and tail. */
export function shortHash(hash: string, head = 10, tail = 6): string {
  if (!hash) return DASH_PLACEHOLDER;
  if (hash.length <= head + tail + 1) return hash;
  return `${hash.slice(0, head)}…${hash.slice(-tail)}`;
}

/** Risk grade -> tailwind-ish semantic colour key. */
export function riskTone(grade: string): 'critical' | 'high' | 'medium' | 'low' {
  const g = (grade || '').toUpperCase();
  if (g.startsWith('CRIT') || g === 'E' || g === 'F') return 'critical';
  if (g.startsWith('HIGH') || g === 'D') return 'high';
  if (g.startsWith('MED') || g === 'C') return 'medium';
  return 'low';
}

/** Severity 1-5 -> label. */
export function severityLabel(severity: number): string {
  return (
    ['', 'Informational', 'Low', 'Moderate', 'High', 'Critical'][severity] ??
    'Unknown'
  );
}

/** Clipboard write that degrades gracefully when the API is unavailable. */
export async function copyText(text: string): Promise<boolean> {
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch {
    /* fall through to the legacy path */
  }
  try {
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.setAttribute('readonly', '');
    ta.style.position = 'fixed';
    ta.style.opacity = '0';
    document.body.appendChild(ta);
    ta.select();
    const ok = document.execCommand('copy');
    ta.remove();
    return ok;
  } catch {
    return false;
  }
}

/**
 * Estimate passphrase strength locally (zero network, no wordlist download).
 * Mirrors the intent of `CipherVault.passphrase_strength` on the server; the
 * server remains authoritative, this is purely for live operator feedback.
 */
export function passphraseStrength(pw: string): {
  score: 0 | 1 | 2 | 3 | 4;
  label: string;
  hint: string;
} {
  if (!pw) return { score: 0, label: 'Empty', hint: 'Enter a passphrase.' };

  let bits = 0;
  const classes =
    Number(/[a-z]/.test(pw)) +
    Number(/[A-Z]/.test(pw)) +
    Number(/[0-9]/.test(pw)) +
    Number(/[^A-Za-z0-9]/.test(pw));
  const alphabet =
    (/[a-z]/.test(pw) ? 26 : 0) +
    (/[A-Z]/.test(pw) ? 26 : 0) +
    (/[0-9]/.test(pw) ? 10 : 0) +
    (/[^A-Za-z0-9]/.test(pw) ? 33 : 0);
  if (alphabet > 0) bits = Math.log2(alphabet) * pw.length;

  // Penalise obvious repetition and sequences.
  if (/(.)\1{2,}/.test(pw)) bits *= 0.75;
  if (/(?:abc|123|qwe|password|admin|letmein)/i.test(pw)) bits *= 0.5;

  if (pw.length < 8) {
    return {
      score: 0,
      label: 'Too short',
      hint: 'Minimum 8 characters required by the vault.',
    };
  }
  if (bits < 45) {
    return {
      score: 1,
      label: 'Weak',
      hint: 'Add length and mix character classes.',
    };
  }
  if (bits < 70) {
    return {
      score: 2,
      label: 'Fair',
      hint: classes < 3 ? 'Mix upper, lower, digits and symbols.' : 'Add length.',
    };
  }
  if (bits < 100) {
    return { score: 3, label: 'Strong', hint: 'Good. Store it in your vault.' };
  }
  return {
    score: 4,
    label: 'Very strong',
    hint: 'Excellent entropy. Losing it means losing the data.',
  };
}
