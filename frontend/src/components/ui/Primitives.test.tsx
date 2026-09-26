import { Badge, Button, Panel, inputClass } from './Primitives';

describe('UI Primitives', () => {
  test('exports core primitive components and styles', () => {
    expect(typeof Button).toBe('function');
    expect(typeof Badge).toBe('function');
    expect(typeof Panel).toBe('function');
    expect(typeof inputClass).toBe('string');
  });

  test('inputClass contains required base utilities', () => {
    expect(inputClass).toContain('rounded');
    expect(inputClass).toContain('border');
  });
});
