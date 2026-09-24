/**
 * AetherMask (CipherShift) :: SPA entry point
 *
 * Wraps the Data Studio in:
 *   - React.StrictMode          - surfaces unsafe lifecycles during dev
 *   - MotionConfig reducedMotion="user"
 *         Globally honours `prefers-reduced-motion`, satisfying WCAG 2.3.3
 *         without every component having to call useReducedMotion().
 *   - LazyMotion (domAnimation, strict)
 *         Ships the ~4.6 kB `m` feature bundle instead of the ~34 kB full
 *         `motion` component. `strict` makes any accidental use of the heavy
 *         <motion.*> component throw at development time.
 */

import React from 'react';
import ReactDOM from 'react-dom/client';
import { LazyMotion, domAnimation, MotionConfig } from 'motion/react';
import DataStudio from './components/DataStudio';
import { ToastProvider } from './components/ui/Toasts';
import './index.css';

const container = document.getElementById('root');
if (!container) {
  throw new Error('AetherMask: #root mount point missing from index.html');
}

ReactDOM.createRoot(container).render(
  <React.StrictMode>
    <MotionConfig reducedMotion="user">
      <LazyMotion features={domAnimation} strict>
        <ToastProvider>
          <DataStudio />
        </ToastProvider>
      </LazyMotion>
    </MotionConfig>
  </React.StrictMode>,
);
