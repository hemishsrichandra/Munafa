const { test, expect } = require('@playwright/test');
const fs = require('node:fs');

test('phone signup, logout and existing account sign-in', async ({ page }) => {
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  await page.getByRole('button', { name: 'Create account', exact: true }).click();
  for (const width of [320, 360, 390, 430]) {
    await page.setViewportSize({ width, height: 844 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
      true,
    );
  }
  const username = `phone-owner-${Date.now()}`;
  await page.getByLabel('Store name', { exact: true }).fill('Synthetic signup test kirana');
  await page.getByLabel('Username', { exact: true }).fill(username);
  await page.getByLabel('Password', { exact: true }).fill('synthetic-onboarding-password');
  await page.getByLabel('Confirm password', { exact: true }).fill('different-test-password');
  await page.getByRole('button', { name: 'Create account', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('Passwords do not match');
  await page.getByLabel('Confirm password', { exact: true }).fill('synthetic-onboarding-password');
  fs.mkdirSync('artifacts/test-evidence', { recursive: true });
  await page.screenshot({ path: 'artifacts/test-evidence/signup-phone.png', fullPage: true });
  await page.getByRole('button', { name: 'Create account', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Today', exact: true })).toBeVisible();
  expect((await (await page.request.get('/api/auth/me')).json()).store.demo).toBe(false);
  expect(await (await page.request.get('/api/cases')).json()).toEqual([]);
  page.on('dialog', (d) => d.accept());
  await page.getByRole('button', { name: 'More', exact: true }).click();
  await page.getByRole('button', { name: 'Sign out', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Sign in', exact: true })).toBeVisible();
  await page.getByLabel('Username', { exact: true }).fill(username.toUpperCase());
  await page.getByLabel('Password', { exact: true }).fill('synthetic-onboarding-password');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Today', exact: true })).toBeVisible();
  expect(errors).toEqual([]);
});

test('public demo needs no access code and remains private between visitors', async ({
  page,
  browser,
}) => {
  await page.setViewportSize({ width: 360, height: 800 });
  await page.goto('/');
  await expect(page.getByText('Explore a private demo', { exact: false })).toBeVisible();
  await page.getByRole('button', { name: 'Try a demo', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Today', exact: true })).toBeVisible();
  const a = await (await page.request.get('/api/auth/me')).json();
  const cases = await (await page.request.get('/api/cases')).json();
  expect(a.store.demo).toBe(true);
  expect(cases).toHaveLength(1);
  await page.screenshot({ path: 'artifacts/test-evidence/public-demo-phone.png', fullPage: true });
  const second = await browser.newContext();
  try {
    const other = await second.newPage();
    await other.goto('/');
    await other.getByRole('button', { name: 'Try a demo', exact: true }).click();
    await expect(other.getByRole('heading', { name: 'Today', exact: true })).toBeVisible();
    const b = await (await other.request.get('/api/auth/me')).json();
    expect(b.store.id).not.toBe(a.store.id);
    expect((await other.request.get(`/api/cases/${cases[0].id}`)).status()).toBe(404);
  } finally {
    await second.close();
  }
});
