const { test, expect } = require('@playwright/test');
const fs = require('node:fs');
async function login(page, name) {
  await page.goto('/');
  await page.getByLabel('Username', { exact: true }).fill(name);
  await page.getByLabel('Password', { exact: true }).fill('isolated-browser-test-password');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Today · आज', exact: true })).toBeVisible();
}
async function get(page, path) {
  return page.evaluate(async (p) => {
    const r = await fetch('/api' + p);
    if (!r.ok) throw Error('Read failed: ' + r.status);
    return r.json();
  }, path);
}

test('phone bill photo → reviewed purchase → receipt → shortage → promise → partial/full proof recovery', async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.emulateMedia({ reducedMotion: 'reduce' });
  const errors = [],
    consoleErrors = [];
  page.on('console', (m) => {
    if (m.type() === 'error' && !/^Failed to load resource:.*status of 401/.test(m.text()))
      consoleErrors.push(m.text());
  });
  page.on('pageerror', (e) => errors.push(e.message));
  await login(page, 'release-owner');
  expect((await get(page, '/auth/me')).store.demo).toBe(true);
  const network = await page.context().newCDPSession(page);
  await network.send('Network.enable');
  await network.send('Network.emulateNetworkConditions', {
    offline: false,
    latency: 80,
    downloadThroughput: 200000,
    uploadThroughput: 100000,
  });
  await page.evaluate(() => navigator.serviceWorker.ready);
  await page.getByRole('button', { name: 'Deliveries & Stock', exact: true }).click();
  await page.getByRole('button', { name: 'stock', exact: true }).click();
  await page.getByRole('button', { name: 'New Item', exact: true }).click();
  await page.getByLabel('code', { exact: true }).fill('RELEASE-RICE');
  await page.getByLabel('name', { exact: true }).fill('Rice');
  await page.getByRole('combobox', { name: 'Unit', exact: true }).selectOption('kg');
  await page.getByRole('button', { name: 'Save Item', exact: true }).click();
  await page.getByRole('button', { name: 'purchases', exact: true }).click();
  await page.getByRole('button', { name: 'Add New Bill · बिल जोड़ें', exact: true }).click();
  await page
    .getByLabel('Bill photo or PDF', { exact: true })
    .setInputFiles('evaluation/corpus/images/fractional.png');
  await page.getByRole('button', { name: 'Read document', exact: true }).click();
  await expect(
    page.getByText(
      'Check the bill details before confirming. Enter delivered quantities separately.',
    ),
  ).toBeVisible();
  expect(
    (await get(page, '/purchases'))[0].revisions.some((r) =>
      /Cloud extraction is not configured/.test(r.provenance?.warning || ''),
    ),
  ).toBe(true);
  // Manual review of this exact public synthetic source: 2.5 kg @ ₹80 = ₹200.
  await page.getByLabel('Supplier', { exact: true }).fill('Synthetic Wholesale 11');
  await page.getByLabel('Invoice reference', { exact: true }).fill('SYNTH-11');
  await page.getByLabel('Invoice date', { exact: true }).fill('2026-10-29');
  await page.getByLabel('Description', { exact: true }).fill('ಅಕ್ಕಿ / चावल');
  await page
    .getByRole('combobox', { name: 'Reviewed Item', exact: true })
    .selectOption({ label: 'Rice (kg)' });
  await page.getByRole('combobox', { name: 'Unit', exact: true }).selectOption('kg');
  await page.getByLabel('Billed quantity', { exact: true }).fill('2.5');
  await page.getByLabel('Unit price (₹)', { exact: true }).fill('80');
  await page.getByLabel('Claim price per unit (₹)', { exact: true }).fill('80');
  await page.getByLabel('Tax (₹)', { exact: true }).fill('0');
  await page.getByLabel('Discount (₹)', { exact: true }).fill('0');
  await page.getByLabel('Invoice total (₹)', { exact: true }).fill('200');
  await page.getByRole('button', { name: 'Save invoice draft', exact: true }).click();
  await page
    .getByRole('button', { name: 'Save checked bill · stock stays the same', exact: true })
    .click();
  expect((await get(page, '/products'))[0].stock_quantity).toBe('0');
  await page
    .getByRole('button', { name: 'Count Delivered Items · सामान की गिनती', exact: true })
    .click();
  await page.getByLabel('Actual quantity', { exact: true }).fill('2');
  await page.getByLabel('Damaged quantity', { exact: true }).fill('0');
  await page.getByText('I checked the units.', { exact: true }).click();
  await page.getByText('Delivery is complete', { exact: true }).click();
  await page.getByText('Effective prices verified', { exact: true }).click();
  await page.getByRole('button', { name: 'Save receiving draft', exact: true }).click();
  await page.getByRole('button', { name: 'Review receiving draft', exact: true }).click();
  await page
    .getByRole('button', { name: 'Accept reviewed receiving and update stock', exact: true })
    .click();
  await expect(page.getByText(/Accepted receipt/)).toBeVisible();
  expect((await get(page, '/products'))[0].stock_quantity).toBe('2');
  const purchase = (await get(page, '/purchases'))[0],
    cid = purchase.case_id;
  await page.getByRole('button', { name: 'Open supplier recovery case', exact: true }).click();
  await page.getByRole('button', { name: 'Confirm shortage', exact: true }).click();
  await expect
    .poll(async () => (await get(page, '/cases/' + cid)).approved_amount_paise)
    .toBe(4000);
  await page.getByRole('button', { name: 'Prepare supplier message', exact: true }).click();
  await expect(page.locator('.message-preview')).toContainText('INR 40.00');
  await expect(page.getByRole('link', { name: 'Open WhatsApp' })).toHaveAttribute(
    'href',
    /^https:\/\/wa.me\//,
  );
  await page.getByRole('button', { name: 'Close dialog', exact: true }).click();
  // Explicit simulated handoff only. No WhatsApp window is opened or message sent.
  await page
    .getByRole('checkbox', { name: 'I have sent the approved evidence to the supplier.' })
    .check();
  await page.getByRole('button', { name: 'Yes, I sent the evidence' }).click();
  await page.getByRole('button', { name: 'Record supplier promise', exact: true }).click();
  await page
    .getByLabel('What did the supplier say?')
    .fill('Synthetic promise: ₹20 next bill, balance later.');
  await page.getByRole('button', { name: 'Save promise', exact: true }).click();
  await expect.poll(async () => (await get(page, '/cases/' + cid)).status).toBe('promised');
  expect((await get(page, '/cases/' + cid)).recovered_paise).toBe(0);
  for (const [index, status] of [
    [0, 'partial'],
    [1, 'resolved'],
  ]) {
    await page
      .getByRole('button', { name: 'Record Money Received · पैसा वापस मिला', exact: true })
      .click();
    await page.getByLabel('Money actually received or reduced from a bill (₹)').fill('20');
    await page.getByRole('button', { name: 'Load synthetic next-bill credit' }).click();
    const href = await page
      .getByRole('link', { name: 'Open and inspect attached evidence' })
      .getAttribute('href');
    expect(await page.evaluate(async (url) => (await fetch(url)).text(), href)).toContain(
      'SYNTHETIC EVIDENCE',
    );
    await expect(
      page.getByRole('button', { name: 'Confirm money received', exact: true }),
    ).toBeDisabled();
    await page.getByRole('checkbox', { name: /I checked this proof/ }).check();
    await page.getByRole('button', { name: 'Confirm money received', exact: true }).click();
    await expect.poll(async () => (await get(page, '/cases/' + cid)).status).toBe(status);
    expect((await get(page, '/cases/' + cid)).recovered_paise).toBe((index + 1) * 2000);
  }
  const sku = (await get(page, '/products'))[0];
  expect(sku.stock_quantity).toBe('2');
  expect((await get(page, `/products/${sku.id}/movements`)).events).toHaveLength(1);
  await expect(page.getByRole('heading', { name: 'Every rupee, accounted for.' })).toBeVisible();
  await page.screenshot({
    path: 'artifacts/test-evidence/batch10-integrated-recovery.png',
    fullPage: true,
  });
  expect(errors).toEqual([]);
  expect(consoleErrors).toEqual([]);
});

test('throttled startup, keyboard dialog, offline warm launch and production shell metadata', async ({
  page,
  context,
}) => {
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  const cdp = await context.newCDPSession(page);
  await cdp.send('Emulation.setCPUThrottlingRate', { rate: 4 });
  await cdp.send('Network.enable');
  await cdp.send('Network.emulateNetworkConditions', {
    offline: false,
    latency: 120,
    downloadThroughput: 200000,
    uploadThroughput: 100000,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  const start = Date.now();
  await login(page, 'release-performance');
  const ready = Date.now() - start;
  await page.evaluate(() => navigator.serviceWorker.ready);
  const touch = await page.locator('.bottom-nav button').evaluateAll((els) =>
    els.map((e) => ({
      width: e.getBoundingClientRect().width,
      height: e.getBoundingClientRect().height,
    })),
  );
  expect(touch.every((r) => r.width >= 44 && r.height >= 44)).toBe(true);
  await expect(page.getByRole('button', { name: 'Install app', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Install app', exact: true }).click();
  await expect(page.locator('.install-guide')).toBeVisible();
  await page.getByRole('button', { name: 'Install app', exact: true }).click();
  await page.getByRole('button', { name: 'Add New Bill · बिल जोड़ें', exact: true }).click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await page.getByRole('button', { name: 'Enter manually', exact: true }).click();
  await page.getByRole('dialog').focus();
  const contrast = await page.evaluate(() => {
    const rgb = (value) => (value.match(/[\d.]+/g) || []).slice(0, 3).map(Number);
    const lum = (c) =>
      c
        .map((v) => {
          v /= 255;
          return v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
        })
        .reduce((sum, v, i) => sum + v * [0.2126, 0.7152, 0.0722][i], 0);
    return ['.field', '.metric-foot', '.button.primary:not(:disabled)'].map((selector) => {
      const el = document.querySelector(selector);
      if (!el) return { selector, ratio: null };
      let node = el,
        bg = '';
      while (node) {
        bg = getComputedStyle(node).backgroundColor;
        if (bg !== 'rgba(0, 0, 0, 0)' && bg !== 'transparent') break;
        node = node.parentElement;
      }
      const a = lum(rgb(getComputedStyle(el).color)),
        b = lum(rgb(bg || 'rgb(255,255,255)'));
      return { selector, ratio: (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05) };
    });
  });
  expect(
    contrast.every((c) => c.ratio !== null && c.ratio >= 4.5),
    JSON.stringify(contrast),
  ).toBe(true);
  await page.keyboard.press('Shift+Tab');
  expect(
    await page.evaluate(() =>
      document.querySelector('[role=dialog]').contains(document.activeElement),
    ),
  ).toBe(true);
  await page.keyboard.press('Tab');
  expect(
    await page.evaluate(() =>
      document.querySelector('[role=dialog]').contains(document.activeElement),
    ),
  ).toBe(true);
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).toHaveCount(0);
  await page.getByRole('button', { name: 'Saved on Phone', exact: true }).click();
  await expect(page.getByText('Sync diagnostics (development only)', { exact: true })).toHaveCount(
    0,
  );
  await cdp.send('Network.emulateNetworkConditions', {
    offline: false,
    latency: 0,
    downloadThroughput: -1,
    uploadThroughput: -1,
  });
  await context.setOffline(true);
  const offlineStart = Date.now();
  await page.reload();
  await expect(page.getByRole('heading', { name: 'Drafts & sync', exact: true })).toBeVisible();
  const offlineLaunch = Date.now() - offlineStart;
  for (const viewport of [
    { width: 360, height: 800 },
    { width: 430, height: 932 },
    { width: 768, height: 1024 },
    { width: 1440, height: 1080 },
  ]) {
    await page.setViewportSize(viewport);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
      true,
    );
  }
  fs.mkdirSync('artifacts/test-evidence', { recursive: true });
  fs.writeFileSync(
    'artifacts/test-evidence/batch10-browser-performance.json',
    JSON.stringify(
      {
        sample_size: 1,
        environment:
          'Headless Chromium local PostgreSQL; simulated network and 4x CPU slowdown, not a physical low-end device',
        cpu_slowdown_rate: 4,
        network: {
          latency_ms: 120,
          download_bytes_per_second: 200000,
          upload_bytes_per_second: 100000,
        },
        navigation_through_scripted_login_to_home_ms: ready,
        tested_text_contrast_ratios: contrast,
        offline_warm_launch_to_drafts_ms: offlineLaunch,
        limitations: [
          'Includes automated form fill/login; not a field performance benchmark or Web Vitals measurement.',
          'Physical device, real radio instability and OS installation not tested.',
        ],
      },
      null,
      2,
    ),
  );
  await context.setOffline(false);
  expect(errors).toEqual([]);
});
