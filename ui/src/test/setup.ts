import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach, vi } from 'vitest';

class MockObserver {
  observe() {}

  disconnect() {}

  takeRecords() {
    return [];
  }
}

if (typeof globalThis.MutationObserver !== 'function') {
  Object.defineProperty(globalThis, 'MutationObserver', {
    configurable: true,
    value: MockObserver,
    writable: true,
  });
}

if (typeof globalThis.ResizeObserver !== 'function') {
  Object.defineProperty(globalThis, 'ResizeObserver', {
    configurable: true,
    value: MockObserver,
    writable: true,
  });
}

if (typeof globalThis.IntersectionObserver !== 'function') {
  Object.defineProperty(globalThis, 'IntersectionObserver', {
    configurable: true,
    value: MockObserver,
    writable: true,
  });
}

if (typeof window.matchMedia !== 'function') {
  Object.defineProperty(window, 'matchMedia', {
    configurable: true,
    value: (query: string) => ({
      addEventListener: () => {},
      addListener: () => {},
      dispatchEvent: () => false,
      matches: false,
      media: query,
      onchange: null,
      removeEventListener: () => {},
      removeListener: () => {},
    }),
    writable: true,
  });
}

if (typeof Element.prototype.scrollIntoView !== 'function') {
  Object.defineProperty(Element.prototype, 'scrollIntoView', {
    configurable: true,
    value: () => {},
    writable: true,
  });
}

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});
