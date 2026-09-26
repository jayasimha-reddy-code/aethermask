/// <reference types="vite/client" />

/** Injected by `define` in vite.config.ts. */
declare const __AETHERMASK_UI_VERSION__: string;

declare function describe(name: string, fn: () => void): void;
declare function test(name: string, fn: () => void | Promise<void>): void;
declare function it(name: string, fn: () => void | Promise<void>): void;
declare function expect(actual: unknown): {
  toBe(expected: unknown): void;
  toEqual(expected: unknown): void;
  toBeNull(): void;
  toContain(expected: unknown): void;
  toThrow(): void;
  toBeGreaterThanOrEqual(expected: number): void;
};
