const { defineConfig } = require('@playwright/test');
const path = require('node:path');
const python =
  process.env.STARTER_TEST_PYTHON ||
  path.join(
    process.cwd(),
    '.venv',
    process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python',
  );
module.exports = defineConfig({
  testDir: './tests',
  workers: 1,
  timeout: 30000,
  use: {
    baseURL: 'http://127.0.0.1:8011',
    headless: true,
    launchOptions: process.env.PLAYWRIGHT_EXECUTABLE_PATH
      ? { executablePath: process.env.PLAYWRIGHT_EXECUTABLE_PATH }
      : {},
  },
  webServer: {
    command: `"${python}" scripts/serve_e2e.py`,
    url: 'http://127.0.0.1:8011/api/health',
    reuseExistingServer: false,
    timeout: 30000,
  },
});
