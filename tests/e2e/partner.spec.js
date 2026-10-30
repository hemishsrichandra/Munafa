const { test, expect } = require('@playwright/test');
async function login(page) {
  await page.goto('/');
  await page.getByLabel('Username', { exact: true }).fill('partner-owner');
  await page.getByLabel('Password', { exact: true }).fill('isolated-browser-test-password');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Daily business brief' })).toBeVisible();
}
async function request(page, path, body) {
  return page.evaluate(
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
      if (!r.ok) throw Error(await r.text());
      return r.json();
    },
    { path, body },
  );
}
test('evidence brief and synthetic settlement reconciliation are usable on phones', async ({
  page,
}) => {
  await page.setViewportSize({ width: 360, height: 800 });
  await login(page);
  await expect(page.getByText('No connected Paytm data', { exact: true })).toBeVisible();
  await request(page, '/products', {
    code: 'BRIEF-RICE',
    name: 'Brief Rice',
    unit: 'kg',
    reorder_threshold: '2',
  });
  await page.getByRole('button', { name: 'More', exact: true }).click();
  await page.getByRole('button', { name: 'Payments & reconciliation', exact: true }).click();
  await page
    .getByRole('button', { name: 'Load isolated synthetic payment demo', exact: true })
    .click();
  await expect(
    page.getByRole('heading', { name: 'SYNTHETIC DEMO DATA', exact: true }),
  ).toBeVisible();
  await expect(page.getByText(/Recorded payout differs from known components/)).toBeVisible();
  await page.getByRole('button', { name: 'Home', exact: true }).click();
  await expect(
    page.getByRole('heading', { name: 'Check stock: Brief Rice', exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole('heading', { name: 'Review settlement components', exact: true }),
  ).toBeVisible();
  for (const width of [320, 360, 390, 430]) {
    await page.setViewportSize({ width, height: 844 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
      true,
    );
  }
  await page.screenshot({ path: 'test-results/batch6-brief-phone.png', fullPage: true });
  const stock = page
    .getByRole('article')
    .filter({ has: page.getByRole('heading', { name: 'Check stock: Brief Rice' }) });
  await stock.getByRole('button', { name: 'Review source' }).click();
  await expect(page.getByRole('heading', { name: /movement history/ })).toBeVisible();
});
module.exports = { login, request };
