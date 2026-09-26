/**
 * AetherMask (CipherShift) :: client-side egress watchdog
 *
 * Monkey-patches `fetch` and `XMLHttpRequest.open` once, at module scope, to
 * record every network request the SPA issues and to classify it as
 * same-origin or external.
 *
 * WHY THIS EXISTS
 * ---------------
 * The server's `/api/v1/attestation` is a self-report. This hook gives the
 * operator an INDEPENDENT observation from inside the browser: if any
 * dependency ever tried to phone home (an analytics beacon smuggled into a
 * transitive package, a font request, a sourcemap fetch), it would appear
 * here even though the server could not see it.
 *
 * External requests are recorded AND BLOCKED - the patched functions reject
 * rather than allow, so this is an enforcement point, not just telemetry.
 */

import { useEffect, useState } from 'react';

export interface EgressLedger {
  total: number;
  external: string[];
}

const ledger: EgressLedger = { total: 0, external: [] };
const listeners = new Set<(l: EgressLedger) => void>();

function notify(): void {
  const snapshot: EgressLedger = {
    total: ledger.total,
    external: [...ledger.external],
  };
  listeners.forEach((fn) => fn(snapshot));
}

function isExternal(url: string): boolean {
  try {
    const resolved = new URL(url, window.location.href);
    // data:/blob: are in-memory and never leave the machine.
    if (resolved.protocol === 'data:' || resolved.protocol === 'blob:') {
      return false;
    }
    return resolved.origin !== window.location.origin;
  } catch {
    return false;
  }
}

function record(url: string): boolean {
  ledger.total += 1;
  const external = isExternal(url);
  if (external && !ledger.external.includes(url)) {
    ledger.external.push(url);
  }
  notify();
  return external;
}

let nativeFetch: typeof window.fetch | null = null;
let nativeOpen: typeof XMLHttpRequest.prototype.open | null = null;

function patchedFetch(
  input: RequestInfo | URL,
  init?: RequestInit,
): Promise<Response> {
  const url =
    typeof input === 'string'
      ? input
      : input instanceof URL
        ? input.href
        : input.url;
  if (record(url)) {
    return Promise.reject(
      new Error(
        `AetherMask air-gap enforcement: blocked external request to ${url}`,
      ),
    );
  }
  return nativeFetch
    ? nativeFetch(input as RequestInfo, init)
    : window.fetch(input, init);
}

function patchedOpen(
  this: XMLHttpRequest,
  method: string,
  url: string | URL,
  ...rest: unknown[]
) {
  const href = typeof url === 'string' ? url : url.href;
  if (record(href)) {
    throw new Error(
      `AetherMask air-gap enforcement: blocked external XHR to ${href}`,
    );
  }
  if (!nativeOpen) return;
  return (
    nativeOpen as (
      this: XMLHttpRequest,
      m: string,
      u: string | URL,
      ...r: unknown[]
    ) => void
  ).call(this, method, url, ...rest);
}

function observeResourceEntries(list: PerformanceObserverEntryList): void {
  for (const entry of list.getEntries()) {
    const name = entry.name;
    if (isExternal(name) && !ledger.external.includes(name)) {
      ledger.external.push(name);
      notify();
    }
  }
}

/** Install the patches exactly once per page load. */
let installed = false;

function install(): void {
  if (installed || typeof window === 'undefined') return;
  installed = true;

  nativeFetch = window.fetch.bind(window);
  window.fetch = patchedFetch;

  nativeOpen = XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open = patchedOpen as typeof XMLHttpRequest.prototype.open;

  // Passive observation of sub-resource loads (images, styles, scripts) that
  // bypass fetch/XHR entirely. Reported, since they cannot be blocked here.
  if ('PerformanceObserver' in window) {
    try {
      const observer = new PerformanceObserver(observeResourceEntries);
      observer.observe({ entryTypes: ['resource'] });
    } catch {
      /* PerformanceObserver unsupported - fetch/XHR coverage still applies */
    }
  }
}

install();

/** Subscribe a component to the live egress ledger. */
export function useEgressWatch(): EgressLedger {
  const [state, setState] = useState<EgressLedger>(() => ({
    total: ledger.total,
    external: [...ledger.external],
  }));

  useEffect(() => {
    listeners.add(setState);
    setState({ total: ledger.total, external: [...ledger.external] });
    return () => {
      listeners.delete(setState);
    };
  }, []);

  return state;
}
