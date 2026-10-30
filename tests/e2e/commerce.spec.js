const { test, expect } = require('@playwright/test');
async function login(page, name = 'commerce-owner') {
  await page.goto('/');
  await page.getByLabel('Username', { exact: true }).fill(name);
  await page.getByLabel('Password', { exact: true }).fill('isolated-browser-test-password');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Daily business brief' })).toBeVisible();
}
async function request(page, path, body, method = 'POST') {
  return page.evaluate(
    async ({ path, body, method }) => {
      const csrf = decodeURIComponent(
        document.cookie
          .split('; ')
          .find((s) => s.startsWith('pbp_csrf='))
          ?.split('=')[1] || '',
      );
      const r = await fetch('/api' + path, {
        method,
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': csrf,
          'Idempotency-Key': crypto.randomUUID(),
        },
        ...(body ? { body: JSON.stringify(body) } : {}),
      });
      if (!r.ok) throw new Error(await r.text());
      return r.json();
    },
    { path, body, method },
  );
}
test('purchase review, fractional receiving, stock, expiry and linked recovery', async ({
  page,
}) => {
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await login(page);
  await page.getByRole('button', { name: 'Purchases & stock', exact: true }).click();
  await page.getByRole('button', { name: 'stock', exact: true }).click();
  await page.getByRole('button', { name: 'New SKU', exact: true }).click();
  const name = 'Rice-' + Date.now();
  await page.getByLabel('code', { exact: true }).fill(name);
  await page.getByLabel('name', { exact: true }).fill(name);
  await page.getByRole('combobox', { name: 'Unit', exact: true }).selectOption('kg');
  await page.getByRole('button', { name: 'Save SKU', exact: true }).click();
  await expect(page.getByText(name, { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'purchases', exact: true }).click();
  await page.getByRole('button', { name: 'New purchase', exact: true }).click();
  await page.getByLabel('Supplier', { exact: true }).fill('Batch5 Wholesale');
  await page.getByLabel('Invoice reference', { exact: true }).fill(name);
  await page.getByLabel('Description', { exact: true }).fill(name);
  await page
    .getByRole('combobox', { name: 'Reviewed SKU', exact: true })
    .selectOption({ label: `${name} (kg)` });
  await page.getByRole('combobox', { name: 'Unit', exact: true }).selectOption('kg');
  await page.getByLabel('Billed quantity (decimal)', { exact: true }).fill('2.5');
  await page.getByLabel('Printed unit price (paise)', { exact: true }).fill('8000');
  await page.getByLabel('Effective claim unit price (paise)', { exact: true }).fill('8000');
  await page.getByLabel('Invoice total (paise)', { exact: true }).fill('20000');
  await page.getByRole('button', { name: 'Save invoice draft', exact: true }).click();
  await page
    .getByRole('button', { name: 'Confirm reviewed invoice (no stock change)', exact: true })
    .click();
  await expect(page.getByRole('heading', { name: 'Accepted bill lines' })).toBeVisible();
  const products = await request(page, '/products', null, 'GET');
  expect(products.find((p) => p.name === name).stock_quantity).toBe('0');
  await page.getByRole('button', { name: 'Record physical delivery', exact: true }).click();
  await page.getByLabel('Actual quantity', { exact: true }).fill('2');
  await page.getByLabel('Damaged quantity', { exact: true }).fill('0.5');
  await page.getByLabel('Batch reference', { exact: true }).fill(name);
  await page.getByLabel('Expiry date', { exact: true }).fill(new Date().toISOString().slice(0, 10));
  await page.getByText('I checked the units.', { exact: true }).click();
  await page.getByText('Delivery is complete', { exact: true }).click();
  await page.getByText('Effective prices verified', { exact: true }).click();
  await page.getByRole('button', { name: 'Save receiving draft', exact: true }).click();
  await page.getByRole('button', { name: 'Review receiving draft', exact: true }).click();
  await page
    .getByRole('button', { name: 'Accept reviewed receiving and update stock', exact: true })
    .click();
  await expect(page.getByText(/Accepted receipt/)).toBeVisible();
  const after = await request(page, '/products', null, 'GET');
  expect(after.find((p) => p.name === name).stock_quantity).toBe('1.5');
  await page.getByRole('button', { name: 'Open supplier recovery case', exact: true }).click();
  await expect(page.getByRole('heading', { name: `Invoice ${name}`, exact: true })).toBeVisible();
  expect(errors).toEqual([]);
});
test('phone purchase drafts and attached evidence survive offline reload', async ({
  page,
  context,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await login(page, 'commerce-offline');
  await page.getByRole('button', { name: 'Purchases', exact: true }).click();
  await page.getByRole('button', { name: 'New purchase', exact: true }).click();
  await page.getByLabel('Supplier', { exact: true }).fill('Offline commerce');
  await page.getByLabel('Invoice reference', { exact: true }).fill('OFF-B5');
  await page.getByLabel('Bill photo or PDF', { exact: true }).setInputFiles({
    name: 'invoice.pdf',
    mimeType: 'application/pdf',
    buffer: Buffer.from('%PDF-1.4\nSynthetic B5 proof'),
  });
  await context.setOffline(true);
  await page.getByRole('button', { name: 'Save purchase on device', exact: true }).click();
  await expect(
    page.getByText('Saved on this device. Queue from Drafts & sync.', { exact: true }),
  ).toBeVisible();
  await page.reload();
  await expect(page.getByRole('heading', { name: 'Drafts & sync', exact: true })).toBeVisible();
  await expect(page.getByText('purchase: OFF-B5', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Edit draft', exact: true }).click();
  await expect(page.getByLabel('supplier', { exact: true })).toHaveValue('Offline commerce');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: 'test-results/batch5-offline-phone.png', fullPage: true });
});
