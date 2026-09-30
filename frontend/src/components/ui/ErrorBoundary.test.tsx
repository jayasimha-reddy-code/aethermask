import { ErrorBoundary } from './ErrorBoundary';

describe('ErrorBoundary component', () => {
  test('ErrorBoundary is a valid component class', () => {
    expect(typeof ErrorBoundary).toBe('function');
  });

  test('static getDerivedStateFromError captures error', () => {
    const err = new Error('Test fault');
    const state = ErrorBoundary.getDerivedStateFromError(err);
    expect(state.hasError).toBe(true);
    expect(state.error).toBe(err);
  });
});
