/**
 * AetherMask (CipherShift) :: ErrorBoundary
 *
 * Catches unhandled runtime exceptions in subtree components (such as table
 * grids or chart visualizers) to prevent full-screen whiteouts.
 */

import { Component, type ErrorInfo, type ReactNode } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import { Button } from './Primitives';

interface Props {
  children: ReactNode;
  fallbackTitle?: string;
  onReset?: () => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  override state: State = {
    hasError: false,
    error: null,
  };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  override componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    if (import.meta.env?.DEV) {
      console.error('[ErrorBoundary caught error]:', error, errorInfo);
    }
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
    this.props.onReset?.();
  };

  override render() {
    if (this.state.hasError) {
      const title = this.props.fallbackTitle ?? 'Component rendering failed';
      const detail = this.state.error?.message || 'An unexpected runtime error occurred';

      return (
        <div className="flex h-full min-h-[180px] w-full flex-col items-center justify-center rounded-xl border border-caution-500/30 bg-abyss-900/80 p-6 text-center">
          <div className="flex size-10 items-center justify-center rounded-lg border border-caution-500/40 bg-caution-500/10 text-caution-400">
            <AlertTriangle size={18} aria-hidden="true" />
          </div>
          <h3 className="mt-3 text-xs font-semibold text-slate-200">{title}</h3>
          <p className="mt-1 max-w-md text-xs text-slate-400">{detail}</p>
          <div className="mt-4">
            <Button
              tone="neutral"
              icon={<RefreshCw size={12} />}
              onClick={this.handleReset}
            >
              Retry component
            </Button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
