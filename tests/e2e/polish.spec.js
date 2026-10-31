const { test, expect } = require('@playwright/test');
const fs = require('node:fs');

test('merchant screens hide build details and rupee fields send exact integer paise', async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto('/');
  await page.getByLabel('Username', { exact: true }).fill('polish-owner');
  await page.getByLabel('Password', { exact: true }).fill('isolated-browser-test-password');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Today', exact: true })).toBeVisible();
  await expect(page.getByText('No offline drafts', { exact: true })).toBeVisible();
  await expect(
    page.getByText(/Hackathon prototype|API_KEY|IndexedDB|evaluation|PILOT NOT RUN/),
  ).toHaveCount(0);
  await page.getByRole('button', { name: 'Deliveries & Stock', exact: true }).click();
  await page.getByRole('button', { name: 'Add new bill', exact: true }).click();
  await page.getByLabel('Supplier', { exact: true }).fill('SYNTHETIC Cent Wholesale');
  await page.getByLabel('Invoice reference', { exact: true }).fill('UI-CENTS-1');
  await page.getByLabel('Description', { exact: true }).fill('Rice');
  await page.getByLabel('Billed quantity', { exact: true }).fill('2.5');
  await page.getByLabel('Unit price (₹)', { exact: true }).fill('80.055');
  await expect(page.getByLabel('Unit price (₹)', { exact: true })).toHaveAttribute(
    'aria-invalid',
    'true',
  );
  expect(
    await page.getByLabel('Unit price (₹)', { exact: true }).evaluate((e) => e.checkValidity()),
  ).toBe(false);
  await page.getByLabel('Unit price (₹)', { exact: true }).fill('80.05');
  await page.getByLabel('Claim price per unit (₹)', { exact: true }).fill('80.05');
  await page.getByLabel('Invoice total (₹)', { exact: true }).fill('200.13');
  await page.getByText('More bill details · Tax, discount and rounding', { exact: true }).click();
  await page.getByLabel('Rounding (₹)', { exact: true }).fill('-0.01');
  await page.getByLabel('Invoice total (₹)', { exact: true }).fill('200.12');
  const saved = page.waitForResponse(
    (r) => r.url().endsWith('/api/purchases/manual') && r.request().method() === 'POST',
  );
  await page.getByRole('button', { name: 'Save invoice draft', exact: true }).click();
  const response = await saved;
  expect(response.status()).toBe(201);
  const body = response.request().postDataJSON();
  expect(body.lines[0].unit_price_paise).toBe(8005);
  expect(body.lines[0].effective_price_paise).toBe(8005);
  expect(body.total_paise).toBe(20012);
  expect(body.rounding_paise).toBe(-1);
  await expect(
    page.getByText(/Source .*actor|Coordinates not supplied|Confidence not supplied/),
  ).toHaveCount(0);
  await page.getByRole('button', { name: 'Today', exact: true }).click();
  for (const [width, height] of [
    [320, 740],
    [360, 800],
    [390, 844],
    [430, 932],
    [800, 360],
  ]) {
    await page.setViewportSize({ width, height });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
      true,
    );
  }
  fs.mkdirSync('artifacts/test-evidence', { recursive: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({
    path: 'artifacts/test-evidence/polished-home-phone.png',
    fullPage: true,
  });
  await page.getByRole('button', { name: 'More', exact: true }).click();
  await expect(page.getByText(/P2|readiness|prototype|API_KEY/)).toHaveCount(0);
  await page.screenshot({
    path: 'artifacts/test-evidence/polished-more-phone.png',
    fullPage: true,
  });
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.getByRole('button', { name: 'More', exact: true }).click();
  await page.getByRole('button', { name: 'Connections', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Connections', exact: true })).toBeVisible();
  await expect(page.getByText('Not connected', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'More', exact: true }).click();
  await page.getByRole('button', { name: 'Export purchases', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Export purchases', exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  expect(errors).toEqual([]);
});
