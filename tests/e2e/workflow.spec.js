const { merchantNavigate } = require('./navigation.cjs');
const { test, expect } = require('@playwright/test');

let demoCookies;
test.beforeEach(async ({ page, context }) => {
  if (demoCookies) {
    await context.addCookies(demoCookies);
    await page.goto('/');
    await expect(page.getByRole('heading', { name: 'Today · आज', exact: true })).toBeVisible();
    return;
  }
  await page.goto('/');
  await page.getByRole('button', { name: 'Development demo access', exact: true }).click();
  await page.getByLabel('Demo access code').fill('e2e-isolated-demo-access');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Today · आज', exact: true })).toBeVisible();
  demoCookies = await context.cookies();
});

test('merchant completes the A-104 workflow and navigates the ledger', async ({ page }) => {
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Today · आज', exact: true })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Your next delivery starts here' })).toBeVisible();
  await page.screenshot({ path: 'test-results/overview-desktop.png', fullPage: true });
  await page.getByRole('button', { name: 'Add New Bill · बिल जोड़ें', exact: true }).click();
  await page.getByRole('button', { name: 'Use sample invoice' }).click();
  await expect(page.getByRole('heading', { name: 'Invoice A-104', exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Confirm shortage', exact: true })).toBeDisabled();
  const rows = [
    { count: '10', unit: 'pack' },
    { count: '6', unit: 'pack' },
    { count: '24', unit: 'piece' },
  ];
  for (let i = 0; i < 3; i++) {
    await page
      .getByRole('spinbutton', { name: `Item ${i + 1} received quantity`, exact: true })
      .fill(rows[i].count);
    await page
      .getByRole('combobox', { name: `Item ${i + 1} billed unit`, exact: true })
      .selectOption(rows[i].unit);
    await page
      .getByRole('combobox', { name: `Item ${i + 1} received unit`, exact: true })
      .selectOption(rows[i].unit);
    await page.locator('.line-editor').nth(i).getByRole('checkbox').check();
  }
  await page.getByRole('checkbox', { name: /The delivery is complete/ }).check();
  await page.getByRole('checkbox', { name: /I verified effective unit prices/ }).check();
  await page.getByRole('button', { name: 'Save delivery review' }).click();
  await expect(page.getByRole('button', { name: 'Confirm shortage', exact: true })).toBeEnabled();
  await page.getByRole('button', { name: 'Confirm shortage', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Items you counted' })).toBeVisible();
  const downloadPromise = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Download evidence card' }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toMatch(/evidence\.png$/);
  await page.getByRole('button', { name: 'Prepare supplier message' }).click();
  await expect(page.locator('.message-preview')).toContainText(
    'Total reviewed shortage: INR 80.00',
  );
  await page
    .getByRole('checkbox', {
      name: 'I reviewed the message against the approved claim, including amounts and identifiers.',
    })
    .check();
  await expect(page.getByRole('link', { name: 'Open WhatsApp' })).toHaveAttribute(
    'href',
    /^https:\/\/wa.me\//,
  );
  await page
    .getByRole('group', { name: 'Message language' })
    .getByRole('button', { name: 'हिन्दी', exact: true })
    .click();
  await expect(page.getByRole('heading', { name: 'Original English message' })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Open WhatsApp' })).not.toHaveAttribute('href', /./);
  await page
    .getByRole('checkbox', {
      name: 'I reviewed the message against the approved claim, including amounts and identifiers.',
    })
    .check();
  await expect(page.getByRole('link', { name: 'Open WhatsApp' })).toHaveAttribute(
    'href',
    /^https:\/\/wa.me\//,
  );
  await page
    .getByRole('group', { name: 'Message language' })
    .getByRole('button', { name: 'ಕನ್ನಡ', exact: true })
    .click();
  await expect(page.getByRole('heading', { name: 'Original English message' })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Open WhatsApp' })).not.toHaveAttribute('href', /./);
  await page.getByRole('button', { name: 'Close dialog' }).click();
  await page
    .getByRole('checkbox', { name: 'I have sent the approved evidence to the supplier.' })
    .check();
  await page.getByRole('button', { name: 'Yes, I sent the evidence' }).click();
  await page.getByRole('button', { name: 'Record supplier promise' }).click();
  await page.getByLabel('What did the supplier say?').fill('Adjust against next bill.');
  await page.getByRole('button', { name: 'Save promise' }).click();
  await expect(page.getByText('“Adjust against next bill.”')).toBeVisible();
  await page.getByRole('button', { name: 'Record Money Received · पैसा वापस मिला' }).click();
  await page.getByRole('button', { name: 'Load synthetic next-bill credit' }).click();
  await expect(
    page.getByRole('link', { name: 'Open and inspect attached evidence' }),
  ).toBeVisible();
  await page.getByRole('checkbox', { name: /I checked this proof/ }).check();
  await page.getByRole('button', { name: 'Confirm money received' }).click();
  await expect(page.getByRole('heading', { name: 'Every rupee, accounted for.' })).toBeVisible();
  await page.reload();
  await merchantNavigate(page, 'Credit cases');
  await page.getByRole('textbox', { name: 'Search cases' }).fill('A-104');
  await expect(page.getByRole('row', { name: 'Open invoice A-104' })).toContainText(
    'Money received',
  );
  await merchantNavigate(page, 'Suppliers');
  await expect(page.getByRole('heading', { name: 'Shree Ganesh Distributors' })).toBeVisible();
  const performance = page.getByRole('region', { name: 'Supplier performance summaries' });
  await performance.getByText(/Shree Ganesh Distributors · 0 unresolved/).click();
  await expect(performance.getByText(/Time to full recovery:/)).toBeVisible();
  await performance.getByRole('button', { name: 'Open invoice and evidence A-104' }).click();
  await expect(page.getByRole('heading', { name: 'Every rupee, accounted for.' })).toBeVisible();
  await merchantNavigate(page, 'Insights');
  await expect(
    page.getByRole('heading', { name: 'Reviewed value, tracked to resolution' }),
  ).toBeVisible();
  await expect(page.getByRole('button', { name: 'Export CSV', exact: true })).toBeEnabled();
  page.once('dialog', (dialog) => dialog.accept());
  const csvDownload = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Export CSV', exact: true }).click();
  expect((await csvDownload).suggestedFilename()).toBe('supplier-ledger.csv');
  expect(errors).toEqual([]);
});

test('mobile overview, case detail and manual intake are usable without overflow', async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Today · आज', exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  );
  await page.screenshot({ path: 'test-results/overview-mobile.png', fullPage: true });
  await page.getByRole('button', { name: 'More · अन्य', exact: true }).click();
  await merchantNavigate(page, 'Credit cases');
  await page.getByRole('textbox', { name: 'Search cases' }).fill('A-104');
  await page.getByRole('button', { name: 'Open invoice A-104', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Invoice A-104', exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  );
  await page.screenshot({ path: 'test-results/case-mobile.png', fullPage: true });
  await page.getByRole('button', { name: 'Back to workspace' }).click();
  await page.getByRole('button', { name: 'Add New Bill · बिल जोड़ें', exact: true }).click();
  await page.getByRole('button', { name: 'Enter manually' }).click();
  await page.getByLabel('Supplier name').fill('Test Wholesale');
  await page.getByLabel('Invoice reference').fill('MANUAL-01');
  await page.getByRole('textbox', { name: 'Item 1 name', exact: true }).fill('Biscuits');
  await page.getByRole('spinbutton', { name: 'Item 1 billed quantity', exact: true }).fill('1.25');
  await page.getByRole('spinbutton', { name: 'Item 1 unit price', exact: true }).fill('25.50');
  await page.getByRole('button', { name: 'Create draft case' }).click();
  await expect(page.getByRole('heading', { name: 'Invoice MANUAL-01', exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Confirm shortage', exact: true })).toBeDisabled();
  await page.getByRole('combobox', { name: 'Item 1 billed unit', exact: true }).selectOption('kg');
  await page
    .getByRole('spinbutton', { name: 'Item 1 received quantity', exact: true })
    .fill('0.75');
  await page
    .getByRole('combobox', { name: 'Item 1 received unit', exact: true })
    .selectOption('kg');
  await page.locator('.line-editor').getByRole('checkbox').check();
  await page.getByRole('checkbox', { name: /The delivery is complete/ }).check();
  await page.getByRole('checkbox', { name: /I verified effective unit prices/ }).check();
  await page.getByRole('button', { name: 'Save delivery review' }).click();
  await page.getByRole('button', { name: 'Confirm shortage', exact: true }).click();
  await expect(page.locator('.evidence-total')).toHaveText('₹12.75');
  await page.getByRole('button', { name: 'Prepare supplier message' }).click();
  await expect(page.locator('.message-preview')).toContainText(
    'Total reviewed shortage: INR 12.75',
  );
  await page
    .getByRole('group', { name: 'Message language' })
    .getByRole('button', { name: 'हिन्दी', exact: true })
    .click();
  await expect(page.getByRole('heading', { name: 'Original English message' })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Open WhatsApp' })).not.toHaveAttribute('href', /./);
  await page
    .getByRole('checkbox', {
      name: 'I reviewed the message against the approved claim, including amounts and identifiers.',
    })
    .check();
  await expect(page.getByRole('link', { name: 'Open WhatsApp' })).toHaveAttribute(
    'href',
    /^https:\/\/wa.me\//,
  );
  await page
    .getByRole('group', { name: 'Message language' })
    .getByRole('button', { name: 'ಕನ್ನಡ', exact: true })
    .click();
  await expect(page.getByRole('heading', { name: 'Original English message' })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Open WhatsApp' })).not.toHaveAttribute('href', /./);
  await page.getByRole('button', { name: 'Close dialog' }).click();
  await page
    .getByRole('checkbox', { name: 'I have sent the approved evidence to the supplier.' })
    .check();
  await page.getByRole('button', { name: 'Yes, I sent the evidence' }).click();
  await page.getByRole('button', { name: 'Record supplier promise' }).click();
  await page.getByLabel('What did the supplier say?').fill('Synthetic credit on the next bill.');
  await page.getByRole('button', { name: 'Save promise' }).click();
  await expect(page.locator('.evidence-total')).toHaveText('₹12.75');
  await page.getByRole('button', { name: 'Record Money Received · पैसा वापस मिला' }).click();
  await page.getByRole('button', { name: 'Load synthetic next-bill credit' }).click();
  await page.getByRole('checkbox', { name: /I checked this proof/ }).check();
  await page.getByRole('button', { name: 'Confirm money received' }).click();
  await expect(page.getByRole('heading', { name: 'Every rupee, accounted for.' })).toBeVisible();
  await page.screenshot({ path: 'test-results/fractional-recovery-mobile.png', fullPage: true });
});

for (const viewport of [
  { width: 360, height: 800 },
  { width: 390, height: 844 },
  { width: 430, height: 932 },
  { width: 320, height: 740 },
  { width: 800, height: 360 },
]) {
  test(`phone navigation and dialogs ${viewport.width}x${viewport.height}`, async ({ page }) => {
    await page.setViewportSize(viewport);
    const assertFits = async () =>
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
        true,
      );
    await assertFits();
    const mobile = viewport.width <= 760;
    if (mobile) {
      const nav = page.getByRole('navigation', { name: 'Main navigation' });
      const box = await nav.boundingBox();
      expect(box.height).toBeLessThanOrEqual(90);
      const targets = await nav.getByRole('button').all();
      let previousY = null;
      for (const target of targets) {
        const b = await target.boundingBox();
        expect(b.height).toBeGreaterThanOrEqual(44);
        expect(b.width).toBeGreaterThanOrEqual(44);
        if (previousY !== null) expect(Math.abs(b.y - previousY)).toBeLessThan(3);
        previousY = b.y;
      }
    }
    if (mobile) {
      await page.getByRole('button', { name: 'More · अन्य', exact: true }).click();
      await merchantNavigate(page, 'Credit cases');
      await expect(page.getByRole('heading', { name: 'Missing Items & Refunds' })).toBeVisible();
      await page.getByRole('button', { name: 'More · अन्य', exact: true }).click();
      await expect(page.getByRole('heading', { name: 'Manage your business' })).toBeVisible();
      await page.getByLabel('Interface language').selectOption('hi');
      await expect(
        page.getByText('Only navigation labels change.', { exact: false }),
      ).toBeVisible();
      await page.getByLabel('Interface language').selectOption('en');
      await page.getByRole('button', { name: 'Today · आज', exact: true }).click();
    }
    await page.getByRole('button', { name: 'Add New Bill · बिल जोड़ें', exact: true }).click();
    const dialog = page.getByRole('dialog');
    await expect(dialog).toBeVisible();
    await assertFits();
    await page.getByRole('button', { name: 'Enter manually', exact: true }).click();
    await expect(page.getByLabel('Supplier name')).toBeVisible();
    await page.keyboard.press('Tab');
    expect(await dialog.evaluate((el) => el.contains(document.activeElement))).toBe(true);
    await page.getByRole('button', { name: 'Close dialog' }).click();
    await expect(dialog).not.toBeVisible();
    await page.screenshot({
      path: `test-results/phone-${viewport.width}x${viewport.height}.png`,
      fullPage: false,
    });
  });
}

test('manifest, worker and offline app shell isolate authenticated data', async ({
  page,
  context,
}) => {
  const manifest = await page.request.get('/manifest.webmanifest');
  expect(manifest.ok()).toBe(true);
  const metadata = await manifest.json();
  expect(metadata.display).toBe('standalone');
  expect(metadata.scope).toBe('/');
  expect(metadata.icons.length).toBe(3);
  await page.evaluate(() => navigator.serviceWorker.ready);
  await page.reload();
  await expect.poll(() => page.evaluate(() => !!navigator.serviceWorker.controller)).toBe(true);
  const keys = await page.evaluate(async () => {
    const cachesList = await caches.keys();
    let urls = [];
    for (const name of cachesList) {
      const c = await caches.open(name);
      urls.push(...(await c.keys()).map((r) => new URL(r.url).pathname));
    }
    return urls;
  });
  expect(keys.some((p) => p.startsWith('/api/'))).toBe(false);
  expect(keys.some((p) => p === '/index.html')).toBe(true);
  await context.setOffline(true);
  await page.reload();
  await expect(page.getByRole('heading', { name: 'Drafts & sync', exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'New offline invoice' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Sync now', exact: true })).toBeDisabled();
  await page.screenshot({ path: 'test-results/offline-shell.png', fullPage: true });
  await context.setOffline(false);
});
