import React from 'react';
import DataStudio from './components/DataStudio';
import { ToastProvider } from './components/ui/Toasts';

describe('main application bootstrap', () => {
  test('DataStudio and ToastProvider are loadable for root render', () => {
    expect(typeof DataStudio).toBe('function');
    expect(typeof ToastProvider).toBe('function');
  });

  test('React.StrictMode is available', () => {
    expect(typeof React.StrictMode).toBe('symbol');
  });
});
