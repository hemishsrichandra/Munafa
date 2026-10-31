const { test, expect } = require('@playwright/test');
const fs = require('node:fs');

test('install, guidance and offline bars reserve space above the complete app header', async ({
  page,
  context,
}) => {
  await page.goto('/');
  await page.getByLabel('Username', { exact: true }).fill('polish-owner');
  await page.getByLabel('Password', { exact: true }).fill('isolated-browser-test-password');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Today · आज', exact: true })).toBeVisible();
  const assertHeaderFits = async () => {
    await page.evaluate(() => window.scrollTo(0, 0));
    const boxes = await page.evaluate(() => {
      const rect = (selector) => {
        const { top, bottom, left, right } = document
          .querySelector(selector)
          .getBoundingClientRect();
        return { top, bottom, left, right };
      };
      return {
        bar: rect('.pwa-status'),
        navigation: rect('.bottom-nav'),
        header: rect('.topbar'),
        width: innerWidth,
        scrollWidth: document.documentElement.scrollWidth,
      };
    });
    expect(boxes.navigation.top).toBeGreaterThanOrEqual(boxes.bar.bottom - 1);
    expect(boxes.header.top).toBeGreaterThanOrEqual(boxes.bar.bottom - 1);
    expect(boxes.navigation.left).toBeGreaterThanOrEqual(0);
    expect(boxes.navigation.right).toBeLessThanOrEqual(boxes.width);
    expect(boxes.scrollWidth).toBeLessThanOrEqual(boxes.width);
  };
  fs.mkdirSync('artifacts/test-evidence', { recursive: true });
  for (const width of [1470, 1024, 800, 430, 390, 360, 320]) {
    await page.setViewportSize({ width, height: 900 });
    await assertHeaderFits();
    await page.getByRole('button', { name: 'Install app', exact: true }).click();
    await expect(page.locator('.install-guide')).toBeVisible();
    await assertHeaderFits();
    if (width === 1470 || width === 390) {
      await page.screenshot({
        path: `artifacts/test-evidence/header-${width}.png`,
        fullPage: true,
      });
    }
    await page.getByRole('button', { name: 'Install app', exact: true }).click();
  }
  await page.setViewportSize({ width: 1470, height: 900 });
  await page.evaluate(() => window.scrollTo(0, 400));
  await expect
    .poll(() => page.locator('.sidebar').evaluate((e) => e.getBoundingClientRect().top))
    .toBe(0);
  await page.evaluate(() => window.scrollTo(0, 0));
  await context.setOffline(true);
  await expect(page.locator('.pwa-status .offline-banner')).toBeVisible();
  await assertHeaderFits();
  await page.setViewportSize({ width: 360, height: 800 });
  await assertHeaderFits();
  await context.setOffline(false);
});
