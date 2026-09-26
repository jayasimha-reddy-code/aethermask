import type { FramePreview, GridRow, DomainProfileInfo, Stage } from './types';

describe('types verification', () => {
  test('FramePreview contract holds required fields', () => {
    const frame: FramePreview = {
      columns: ['id', 'name'],
      dtypes: ['int', 'string'],
      rows: [[1, 'alpha'], [2, 'beta']],
      total_rows: 2,
      total_columns: 2,
    };
    expect(frame.total_rows).toBe(2);
    expect(frame.columns.length).toBe(2);
  });

  test('GridRow handles heterogeneous cell values', () => {
    const row: GridRow = {
      id: 101,
      tag: 'classified',
      active: true,
      notes: null,
    };
    expect(row.id).toBe(101);
    expect(row.active).toBe(true);
    expect(row.notes).toBeNull();
  });

  test('DomainProfileInfo matches schema', () => {
    const profile: DomainProfileInfo = {
      key: 'defense_to_logistics',
      title: 'Defense to Logistics',
      source_domain: 'Defense',
      cover_domain: 'Commercial Logistics',
      description: 'Obfuscates military terminology to logistics',
      token_rules: 'Deterministic stem mapping',
    };
    expect(profile.key).toBe('defense_to_logistics');
  });

  test('Stage accepts valid pipeline identifiers', () => {
    const validStages: Stage[] = ['ingest', 'profile', 'transform', 'export', 'restore', 'audit'];
    expect(validStages.length).toBe(6);
  });
});
