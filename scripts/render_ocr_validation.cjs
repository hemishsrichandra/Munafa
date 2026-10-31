// Rasterise owned SVG fixtures locally; no font/image/service is fetched remotely.
const { chromium } = require('playwright');
const fs = require('node:fs');
const path = require('node:path');
(async () => {
  const root = path.join(__dirname, '..', 'evaluation', 'validation-v2');
  const manifest = JSON.parse(fs.readFileSync(path.join(root, 'manifest.json'), 'utf8'));
  const browser = await chromium.launch({
    headless: true,
    ...(process.env.PLAYWRIGHT_EXECUTABLE_PATH
      ? { executablePath: process.env.PLAYWRIGHT_EXECUTABLE_PATH }
      : {}),
  });
  try {
    const page = await browser.newPage({
      viewport: { width: 700, height: 760 },
      deviceScaleFactor: 1,
    });
    await page.route('**/*', (route) => route.abort());
    for (const item of manifest.cases) {
      await page.setContent(fs.readFileSync(path.join(root, item.id + '.svg'), 'utf8'));
      await page.evaluate(() => document.fonts.ready);
      await page.locator('svg').screenshot({ path: path.join(root, item.image) });
    }
    process.stdout.write(`Rendered ${manifest.cases.length} synthetic fixtures locally.\n`);
  } finally {
    await browser.close();
  }
})().catch((error) => {
  process.stderr.write(error.message + '\n');
  process.exit(1);
});
