import { easeEmphasized, easeQuick, springSettle } from './motion';

describe('motion system transitions', () => {
  test('easeEmphasized defines restrained tween duration', () => {
    expect(easeEmphasized.duration).toBe(0.24);
    expect(easeEmphasized.type).toBe('tween');
  });

  test('easeQuick defines fast interaction tween', () => {
    expect(easeQuick.duration).toBe(0.16);
    expect(easeQuick.type).toBe('tween');
  });

  test('springSettle uses tween curve rather than bounce spring', () => {
    expect(springSettle.type).toBe('tween');
  });
});
