const { test, expect } = require('@playwright/test');

test('four merchant destinations and quick actions work across phone and desktop', async ({
  page,
}) => {
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto('/');
  await page.getByLabel('Username', { exact: true }).fill('records-owner');
  await page.getByLabel('Password', { exact: true }).fill('isolated-browser-test-password');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  const nav = page.getByRole('navigation', { name: 'Main navigation', exact: true });
  await expect(nav.getByRole('button')).toHaveCount(4);
  for (const width of [320, 390, 844, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    await nav.getByRole('button', { name: 'Today · आज', exact: true }).click();
    await expect(page.getByRole('heading', { name: 'Today · आज', exact: true })).toBeVisible();
    await page.getByRole('button', { name: /Customer Udhaar/ }).click();
    await expect(page.getByRole('combobox', { name: 'Record type', exact: true })).toHaveValue(
      'credit_sale',
    );
    await nav.getByRole('button', { name: 'Today · आज', exact: true }).click();
    await page.getByRole('button', { name: /Settle Galla/ }).click();
    await expect(page.getByRole('region', { name: 'Galla Hisab', exact: true })).toBeVisible();
    await nav.getByRole('button', { name: 'Deliveries & Stock', exact: true }).click();
    await expect(page.getByRole('list', { name: 'Two steps for every delivery' })).toBeVisible();
    await nav.getByRole('button', { name: 'Customer Khata', exact: true }).click();
    await expect(
      page.getByRole('heading', { name: 'Money to Collect · उधार लेना है', exact: true }),
    ).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
      true,
    );
    for (const button of await nav.getByRole('button').all()) {
      const rect = await button.boundingBox();
      expect(rect.height).toBeGreaterThanOrEqual(48);
    }
  }
  await nav.getByRole('button', { name: 'Today · आज', exact: true }).click();
  await page.screenshot({ path: 'artifacts/test-evidence/merchant-today.png', fullPage: true });
  await page
    .getByRole('button', { name: /New Bill/ })
    .first()
    .click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await page.screenshot({ path: 'artifacts/test-evidence/merchant-new-bill.png', fullPage: true });
  expect(errors).toEqual([]);
});
