import { useStudioState } from './useStudioState';

describe('useStudioState', () => {
  test('exports useStudioState hook', () => {
    expect(typeof useStudioState).toBe('function');
  });
});
