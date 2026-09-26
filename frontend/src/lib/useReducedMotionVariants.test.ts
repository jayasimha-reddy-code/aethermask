import { useStageVariants } from './useReducedMotionVariants';

describe('useReducedMotionVariants', () => {
  test('exports hook functions', () => {
    expect(typeof useStageVariants).toBe('function');
  });
});
