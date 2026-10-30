const { defineConfig } = require('@playwright/test');
module.exports = defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false,
  workers: 1,
  timeout: 45000,
  use: {
    baseURL: 'http://127.0.0.1:8001',
    headless: true,
    viewport: { width: 1440, height: 1080 },
    launchOptions: process.env.PLAYWRIGHT_EXECUTABLE_PATH
      ? { executablePath: process.env.PLAYWRIGHT_EXECUTABLE_PATH }
      : {},
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  webServer: {
    command: '.venv/bin/python scripts/serve_e2e.py',
    url: 'http://127.0.0.1:8001/api/health',
    reuseExistingServer: false,
    env: { APP_ENV: 'test', SARVAM_API_KEY: '' },
  },
});
