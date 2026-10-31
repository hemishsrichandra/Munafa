const { test, expect } = require('@playwright/test');

test('merchant saves one-time codes and recovers without exposing codes in offline storage', async ({
  page,
  browser,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  await page.getByLabel('Username', { exact: true }).fill('polish-owner');
  await page.getByLabel('Password', { exact: true }).fill('isolated-browser-test-password');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(
    page.getByRole('heading', { name: 'Daily business brief', exact: true }),
  ).toBeVisible();
  await page.getByRole('button', { name: 'More', exact: true }).click();
  const panel = page.getByRole('region', { name: 'Account recovery', exact: true });
  await panel
    .getByLabel('Current password', { exact: true })
    .fill('isolated-browser-test-password');
  const response = page.waitForResponse(
    (r) => r.url().endsWith('/api/auth/recovery-codes') && r.request().method() === 'POST',
  );
  await panel.getByRole('button', { name: 'Create recovery codes', exact: true }).click();
  const result = await (await response).json();
  expect(result.codes).toHaveLength(8);
  const sheet = page.getByRole('region', { name: 'Save your recovery codes', exact: true });
  await expect(sheet.locator('code')).toHaveCount(8);
  const cached = await page.evaluate(async () => {
    const values = [];
    for (const info of await indexedDB.databases()) {
      const db = await new Promise((resolve, reject) => {
        const r = indexedDB.open(info.name);
        r.onsuccess = () => resolve(r.result);
        r.onerror = () => reject(r.error);
      });
      for (const name of db.objectStoreNames) {
        const rows = await new Promise((resolve, reject) => {
          const r = db.transaction(name).objectStore(name).getAll();
          r.onsuccess = () => resolve(r.result);
          r.onerror = () => reject(r.error);
        });
        values.push(rows);
      }
      db.close();
    }
    return JSON.stringify(values);
  });
  for (const code of result.codes) expect(cached).not.toContain(code);
  await sheet.getByRole('button', { name: 'I saved these codes', exact: true }).click();
  await expect(sheet).toHaveCount(0);
  const other = await browser.newContext();
  try {
    const reset = await other.newPage();
    await reset.goto('/');
    await reset.getByRole('button', { name: 'Recover account', exact: true }).click();
    await reset.getByLabel('Username', { exact: true }).fill('polish-owner');
    await reset.getByLabel('Recovery code', { exact: true }).fill(result.codes[0]);
    const password = '  Recovery-test-password-new  ';
    await reset.getByLabel('New password', { exact: true }).fill(password);
    await reset.getByLabel('Confirm password', { exact: true }).fill(password);
    await reset.getByRole('button', { name: 'Reset password', exact: true }).click();
    await expect(reset.getByRole('status').filter({ hasText: 'Password changed.' })).toBeVisible();
    expect((await page.request.get('/api/auth/me')).status()).toBe(401);
    await reset.getByLabel('Username', { exact: true }).fill('polish-owner');
    await reset.getByLabel('Password', { exact: true }).fill(password);
    await reset.getByRole('button', { name: 'Sign in', exact: true }).click();
    await expect(
      reset.getByRole('heading', { name: 'Daily business brief', exact: true }),
    ).toBeVisible();
    expect((await (await reset.request.get('/api/auth/security')).json()).remaining_codes).toBe(0);
  } finally {
    await other.close();
  }
});
