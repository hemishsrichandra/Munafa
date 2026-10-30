const { test, expect } = require('@playwright/test');
test('standalone starter signs in, navigates phone screens and warms offline shell without fake legal answers', async ({
  page,
  context,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  await page.getByLabel('Username', { exact: true }).fill('synthetic-browser-owner');
  await page.getByLabel('Password', { exact: true }).fill('synthetic-browser-password');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(
    page.getByRole('heading', { name: 'Synthetic foundation browser check' }),
  ).toBeVisible();
  for (const screen of ['My business', 'Updates for me', 'My actions', 'Ask with sources']) {
    await page.getByRole('button', { name: screen, exact: true }).click();
    await expect(page.getByRole('heading', { name: screen, exact: true })).toBeVisible();
    await expect(
      page.getByText('No official sources are connected.', { exact: false }),
    ).toBeVisible();
  }
  for (const width of [320, 360, 390, 430, 1280]) {
    await page.setViewportSize({ width, height: 844 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
      true,
    );
  }
  await page.evaluate(() => navigator.serviceWorker.ready);
  await page.reload();
  await expect
    .poll(() => page.evaluate(() => Boolean(navigator.serviceWorker.controller)))
    .toBe(true);
  const keys = await page.evaluate(async () => {
    const names = await caches.keys();
    const urls = [];
    for (const name of names) {
      const c = await caches.open(name);
      urls.push(...(await c.keys()).map((r) => new URL(r.url).pathname));
    }
    return urls;
  });
  expect(keys.some((k) => k.startsWith('/api/'))).toBe(false);
  await page.getByRole('button', { name: 'Sign out', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Sign in', exact: true })).toBeVisible();
  await context.setOffline(true);
  await page.reload();
  await expect(page.getByText('Offline. Live rules', { exact: false })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Sign in', exact: true })).toBeDisabled();
  await context.setOffline(false);
});
