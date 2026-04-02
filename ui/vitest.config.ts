import { defineConfig } from 'vitest/config';
import viteConfig from './vite.config';

export default defineConfig({
  ...viteConfig,
  test: {
    css: true,
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html'],
    },
    environment: 'jsdom',
    exclude: ['tests/e2e/**'],
    include: ['src/**/*.test.ts', 'src/**/*.test.tsx'],
    // The workspace suites exercise multiple jsdom-heavy panes and lazy surfaces.
    // Running them in parallel workers causes deterministic timeouts even though
    // the individual files pass, so keep the UI harness single-worker.
    maxWorkers: 1,
    setupFiles: './src/test/setup.ts',
  },
});
