const { test, expect } = require('@playwright/test');
const fs = require('node:fs');

test('extension preparation and data gates remain truthful on phones and offline', async ({
  page,
}, testInfo) => {
  await page.setViewportSize({ width: 360, height: 800 });
  await page.goto('/');
  await page.getByLabel('Username', { exact: true }).fill('extension-owner');
  await page.getByLabel('Password', { exact: true }).fill('isolated-browser-test-password');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Today · आज', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'More · अन्य', exact: true }).click();
  await page.getByRole('button', { name: 'Connections', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Connections' })).toBeVisible();
  await expect(page.getByText('Not connected', { exact: true })).toBeVisible();
  await expect(page.getByText(/BLOCKED|SPECIFICATION|API|prototype/)).toHaveCount(0);
  await page.getByRole('button', { name: 'More · अन्य', exact: true }).click();
  await page.getByRole('button', { name: 'Export purchases', exact: true }).click();
  await page.getByRole('button', { name: 'Review purchases', exact: true }).click();
  await expect(page.getByText(/No confirmed purchases in this period/)).toBeVisible();
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
  await page.getByRole('button', { name: 'Review purchases', exact: true }).click();
  await expect(page.getByText('SYNTHETIC Wholesale · SYNTHETIC-EXT-1')).toBeVisible();
  await page.getByRole('button', { name: 'Review download', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Confirm download' })).toBeVisible();
  await page.getByText('View included purchases', { exact: true }).click();
  await expect(
    page.getByRole('heading', { name: 'SYNTHETIC Wholesale · SYNTHETIC-EXT-1' }).last(),
  ).toBeVisible();
  await expect(page.getByText('Recorded tax: ₹0')).toBeVisible();
  await expect(page.locator('pre')).toHaveCount(0);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  const downloadPromise = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Confirm and download', exact: true }).click();
  const download = await downloadPromise;
  const downloadPath = testInfo.outputPath('preparation.json');
  await download.saveAs(downloadPath);
  const pack = JSON.parse(fs.readFileSync(downloadPath, 'utf8'));
  expect(pack.total_recorded_paise).toBe(20000);
  expect(pack.mode).toBe('demo');
  expect(pack.status).toBe('needs_external_review');
  expect(pack.records[0].purchase_id).toBe(purchase.id);
  await expect(page.getByText('Downloaded to your device. Nothing was submitted.')).toBeVisible();
  await page.getByRole('button', { name: 'More · अन्य', exact: true }).click();
  await page.getByRole('button', { name: 'Stock planning', exact: true }).click();
  await expect(page.getByText('Synthetic Rice · kg', { exact: true })).toBeVisible();
  await expect(page.getByText('Not enough sales history for a forecast.')).toBeVisible();
  await expect(page.getByText(/PILOT|schema|evaluation|DATA NOT READY/)).toHaveCount(0);
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
  await page.getByRole('button', { name: 'More · अन्य', exact: true }).click();
  await page.getByRole('button', { name: 'Connections', exact: true }).click();
  await expect(page.getByText('Not connected', { exact: true })).toBeVisible();
  await page.context().setOffline(true);
  await expect(
    page.getByText('You’re offline. Reconnect to refresh connection status.'),
  ).toBeVisible();
  await expect(page.getByRole('button', { name: 'Refresh status', exact: true })).toBeDisabled();
  await page.context().setOffline(false);
  await page.getByRole('button', { name: 'Refresh status', exact: true }).click();
  await expect(
    page.getByText('You’re offline. Reconnect to refresh connection status.'),
  ).toHaveCount(0);
});
