import {
  displayCell,
  formatBytes,
  formatCompact,
  formatInt,
  formatPct,
  passphraseStrength,
  riskTone,
  severityLabel,
  shortHash,
} from './format';

describe('format helpers', () => {
  test('formatBytes formats boundaries correctly', () => {
    expect(formatBytes(0)).toBe('0 B');
    expect(formatBytes(512)).toBe('512 B');
    expect(formatBytes(1024)).toBe('1.0 KB');
    expect(formatBytes(1024 * 1024)).toBe('1.0 MB');
    expect(formatBytes(-1)).toBe('-');
  });

  test('formatInt adds commas to numbers', () => {
    expect(formatInt(1000)).toBe('1,000');
    expect(formatInt(1000000)).toBe('1,000,000');
    expect(formatInt(null)).toBe('-');
  });

  test('formatCompact formats large numbers concisely', () => {
    expect(formatCompact(500)).toBe('500');
    expect(formatCompact(1500)).toContain('1.5');
    expect(formatCompact(null)).toBe('-');
  });

  test('formatPct returns single decimal percentage', () => {
    expect(formatPct(0.5)).toBe('50.0%');
    expect(formatPct(0.1234)).toBe('12.3%');
    expect(formatPct(null)).toBe('-');
  });

  test('displayCell renders primitives safely', () => {
    expect(displayCell(null)).toBe('∅');
    expect(displayCell(undefined)).toBe('∅');
    expect(displayCell(true)).toBe('true');
    expect(displayCell(false)).toBe('false');
    expect(displayCell(42)).toBe('42');
    expect(displayCell('classified')).toBe('classified');
  });

  test('shortHash truncates long strings with ellipsis', () => {
    expect(shortHash('')).toBe('-');
    expect(shortHash('short')).toBe('short');
    expect(shortHash('0123456789abcdef0123456789', 6, 4)).toBe('012345…6789');
  });

  test('riskTone maps grades to semantic keys', () => {
    expect(riskTone('CRITICAL')).toBe('critical');
    expect(riskTone('E')).toBe('critical');
    expect(riskTone('HIGH')).toBe('high');
    expect(riskTone('D')).toBe('high');
    expect(riskTone('MEDIUM')).toBe('medium');
    expect(riskTone('C')).toBe('medium');
    expect(riskTone('A')).toBe('low');
  });

  test('severityLabel returns corresponding label', () => {
    expect(severityLabel(1)).toBe('Informational');
    expect(severityLabel(2)).toBe('Low');
    expect(severityLabel(4)).toBe('High');
    expect(severityLabel(5)).toBe('Critical');
  });

  test('passphraseStrength calculates entropy tiers', () => {
    expect(passphraseStrength('').score).toBe(0);
    expect(passphraseStrength('short').score).toBe(0);
    expect(passphraseStrength('correct-horse-battery-staple-2026!').score).toBeGreaterThanOrEqual(3);
  });
});
