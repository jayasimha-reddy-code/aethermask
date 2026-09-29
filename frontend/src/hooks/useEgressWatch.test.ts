import { useEgressWatch, type EgressLedger } from './useEgressWatch';

describe('useEgressWatch module', () => {
  test('exports hook and types', () => {
    expect(typeof useEgressWatch).toBe('function');
  });

  test('EgressLedger contract requires total and external array', () => {
    const ledger: EgressLedger = { total: 5, external: [] };
    expect(ledger.total).toBe(5);
    expect(Array.isArray(ledger.external)).toBe(true);
  });
});
