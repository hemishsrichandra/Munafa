const { test, expect } = require('@playwright/test');
const fs = require('node:fs');

test('extension preparation and data gates remain truthful on phones and offline', async ({
  page,
}) => {
  await page.setViewportSize({ width: 360, height: 800 });
  await page.goto('/');
  await page.getByLabel('Username', { exact: true }).fill('extension-owner');
  await page.getByLabel('Password', { exact: true }).fill('isolated-browser-test-password');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Daily business brief' })).toBeVisible();
  await page.getByRole('button', { name: 'More', exact: true }).click();
  await page.getByRole('button', { name: 'Connections & readiness', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Connections & readiness' })).toBeVisible();
  await expect(page.getByText('BLOCKED — SPECIFICATION', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Review accepted records', exact: true }).click();
  await expect(page.getByText(/No accepted purchases in this period/)).toBeVisible();
  const call = async (path, body) =>
    page.evaluate(
      async ({ path, body }) => {
        const csrf = decodeURIComponent(
          document.cookie
            .split('; ')
            .find((s) => s.startsWith('pbp_csrf='))
            ?.split('=')[1] || '',
        );
        const r = await fetch('/api' + path, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRF-Token': csrf,
            'Idempotency-Key': crypto.randomUUID(),
          },
          body: JSON.stringify(body),
        });
        if (!r.ok) throw new Error('Test setup API failed: ' + r.status);
        return r.json();
      },
      { path, body },
    );
  const product = await call('/products', {
    code: 'EXT-SYNTHETIC',
    name: 'Synthetic Rice',
    unit: 'kg',
    reorder_threshold: '1',
  });
  const today = await page.getByLabel('Period start', { exact: true }).inputValue();
  const purchase = await call('/purchases/manual', {
    supplier: 'SYNTHETIC Wholesale',
    reference: 'SYNTHETIC-EXT-1',
    date: today,
    lines: [
      {
        description: 'Rice',
        product_id: product.id,
        billed_quantity: '2.5',
        unit: 'kg',
        unit_price_paise: 8000,
        effective_price_paise: 8000,
      },
    ],
    tax_paise: 0,
    discount_paise: 0,
    total_paise: 20000,
  });
  let action = await call('/commerce/proposals', {
    action_type: 'accept_purchase',
    entity_id: purchase.id,
    expected_version: purchase.version,
    payload: {},
  });
  action = await call(`/actions/${action.id}/approve`, {
    version: action.version,
    payload_digest: action.payload_digest,
  });
  await call(`/actions/${action.id}/execute`, { version: action.version });
  await page.getByRole('button', { name: 'Review accepted records', exact: true }).click();
  await expect(page.getByText('SYNTHETIC Wholesale · SYNTHETIC-EXT-1')).toBeVisible();
  await page
    .getByRole('button', { name: 'Prepare local export for approval', exact: true })
    .click();
  await expect(page.getByRole('heading', { name: 'Review exact export' })).toBeVisible();
  await page.getByText('View full export contents', { exact: true }).click();
  await expect(page.locator('pre')).toContainText(purchase.id);
  await expect(page.locator('pre')).toContainText('needs_external_review');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  const downloadPromise = page.waitForEvent('download');
  await page
    .getByRole('button', { name: 'Approve this local export and download', exact: true })
    .click();
  const download = await downloadPromise;
  const pack = JSON.parse(fs.readFileSync(await download.path(), 'utf8'));
  expect(pack.total_recorded_paise).toBe(20000);
  expect(pack.mode).toBe('demo');
  expect(pack.status).toBe('needs_external_review');
  expect(pack.records[0].purchase_id).toBe(purchase.id);
  await expect(
    page.getByText('Preparation pack downloaded. It remains unreviewed; nothing was submitted.'),
  ).toBeVisible();
  await page.getByRole('button', { name: 'Check recorded SKU data', exact: true }).click();
  await expect(page.getByText('Synthetic Rice · kg', { exact: true })).toBeVisible();
  await expect(page.getByText('DATA NOT READY', { exact: true })).toBeVisible();
  await expect(page.getByText(/PILOT NOT RUN/)).toBeVisible();
  for (const width of [320, 360, 390, 430, 844]) {
    await page.setViewportSize({ width, height: 844 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
      true,
    );
  }
  await page.setViewportSize({ width: 390, height: 844 });
  fs.mkdirSync('artifacts/test-evidence', { recursive: true });
  await page.screenshot({
    path: 'artifacts/test-evidence/extension-readiness.png',
    fullPage: true,
  });
  await page.context().setOffline(true);
  await expect(
    page.getByText('Offline. Any displayed status is from this visit; reconnect to refresh.'),
  ).toBeVisible();
  await page.getByRole('button', { name: 'Review accepted records', exact: true }).click();
  await expect(page.getByRole('alert').last()).toBeVisible();
  await page.context().setOffline(false);
  await page.getByRole('button', { name: 'Refresh status', exact: true }).click();
  await expect(page.getByText(/Offline. Any displayed status/)).toHaveCount(0);
});
