import { Kbd, ToastProvider, useToasts } from './Toasts';

describe('Toasts UI', () => {
  test('exports toast container and hooks', () => {
    expect(typeof Kbd).toBe('function');
    expect(typeof ToastProvider).toBe('function');
    expect(typeof useToasts).toBe('function');
  });
});
