// Each group uses a fresh disposable database/server, preserving the production
// login rate limit while keeping commerce and legacy journeys independent.
const { spawn } = require('node:child_process');
const { readdirSync } = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright');
const cli = require.resolve('@playwright/test/cli');
async function main() {
  const files = readdirSync('tests/e2e').filter((f) => f.endsWith('.spec.js'));
  for (const group of [
    files.filter((f) => f === 'commerce.spec.js'),
    files.filter((f) => f === 'partner.spec.js'),
    files.filter((f) => !['commerce.spec.js','partner.spec.js'].includes(f)),
  ]) {
    if (!group.length) continue;
    // A remote connection avoids Windows browser-fixture shutdown hanging after
    // successful tests. The launcher owns this isolated browser's whole lifetime.
    const server =
      process.platform === 'win32'
        ? await chromium.launchServer({
            headless: true,
            ...(process.env.PLAYWRIGHT_EXECUTABLE_PATH
              ? { executablePath: process.env.PLAYWRIGHT_EXECUTABLE_PATH }
              : {}),
          })
        : null;
    let code;
    try {
      code = await new Promise((resolve, reject) => {
        const child = spawn(
          process.execPath,
          [
            cli,
            'test',
            ...group.map((f) => path.posix.join('tests/e2e', f)),
            ...process.argv.slice(2),
          ],
          {
            stdio: 'inherit',
            env: {
              ...process.env,
              ...(server ? { PW_TEST_CONNECT_WS_ENDPOINT: server.wsEndpoint() } : {}),
            },
          },
        );
        child.once('error', reject);
        child.once('exit', (status) => resolve(status ?? 1));
      });
    } finally {
      if (server) {
        // Kill only the browser process created above; never a user's browser.
        await new Promise((resolve) => {
          const killer = spawn('taskkill', ['/PID', String(server.process().pid), '/T', '/F'], {
            stdio: 'ignore',
          });
          killer.once('error', resolve);
          killer.once('exit', resolve);
        });
      }
    }
    if (code !== 0) return code;
  }
  return 0;
}
main().then(
  (code) => process.exit(code),
  (error) => {
    console.error(error);
    process.exit(1);
  },
);
