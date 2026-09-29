import { pipelineStageReducer, type PipelineStageState } from './usePipelineStageReducer';

describe('pipelineStageReducer', () => {
  const initial: PipelineStageState = {
    stage: 'ingest',
    direction: 1,
    visited: new Set(['ingest']),
  };

  test('GO action transitions stage and sets direction', () => {
    const next = pipelineStageReducer(initial, { type: 'GO', target: 'profile' });
    expect(next.stage).toBe('profile');
    expect(next.direction).toBe(1);
    expect(next.visited.has('profile')).toBe(true);
  });

  test('NEXT moves sequentially forward', () => {
    const next = pipelineStageReducer(initial, { type: 'NEXT' });
    expect(next.stage).toBe('profile');
    expect(next.direction).toBe(1);
  });

  test('PREV moves sequentially backward', () => {
    const atProfile: PipelineStageState = {
      stage: 'profile',
      direction: 1,
      visited: new Set(['ingest', 'profile']),
    };
    const prev = pipelineStageReducer(atProfile, { type: 'PREV' });
    expect(prev.stage).toBe('ingest');
    expect(prev.direction).toBe(-1);
  });

  test('RESET returns to ingest stage', () => {
    const atExport: PipelineStageState = {
      stage: 'export',
      direction: 1,
      visited: new Set(['ingest', 'profile', 'transform', 'export']),
    };
    const reset = pipelineStageReducer(atExport, { type: 'RESET' });
    expect(reset.stage).toBe('ingest');
  });
});
