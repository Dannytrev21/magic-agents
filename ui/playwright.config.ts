import { defineConfig } from '@playwright/test';

const supportedBrowsers = new Set(['chromium', 'firefox', 'webkit']);
const requestedBrowser = process.env.PLAYWRIGHT_BROWSER ?? 'chromium';
const browserName = supportedBrowsers.has(requestedBrowser) ? requestedBrowser : 'webkit';
const sharedUse = {
  baseURL: 'http://127.0.0.1:4173',
  browserName,
  screenshot: 'only-on-failure' as const,
  trace: 'retain-on-failure' as const,
  viewport: { width: 1440, height: 980 },
};
const browserUse = browserName === 'chromium' ? { channel: 'chromium' as const } : {};
const webServerCommand = `${JSON.stringify(process.execPath)} ./node_modules/vite/bin/vite.js --host 127.0.0.1 --port 4173`;

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: true,
  projects: [
    {
      name: browserName,
      use: {
        ...sharedUse,
        ...browserUse,
      },
    },
  ],
  reporter: [['list'], ['html', { open: 'never' }]],
  retries: 0,
  webServer: {
    command: webServerCommand,
    port: 4173,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
