import { STAGES, STAGE_INDEX, StageRail } from './StageRail';

describe('StageRail component', () => {
  test('STAGES lists all six pipeline phases in sequence', () => {
    expect(STAGES.map((s) => s.id)).toEqual([
      'ingest',
      'profile',
      'transform',
      'export',
      'restore',
      'audit',
    ]);
  });

  test('STAGE_INDEX maps phases to integer positions', () => {
    expect(STAGE_INDEX.ingest).toBe(0);
    expect(STAGE_INDEX.audit).toBe(5);
  });

  test('StageRail exports component function', () => {
    expect(typeof StageRail).toBe('function');
  });
});
