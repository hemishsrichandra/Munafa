const { test, expect } = require('@playwright/test');
const path = require('node:path');
async function demo(page) {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  await page.getByRole('button', { name: 'Try a demo', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Today', exact: true })).toBeVisible();
}
const picker = (page) => page.getByRole('combobox', { name: /Interface language|ऐप की भाषा/ });
test('language preference persists, new bill protects edits, and saved device drafts are explicit', async ({
  page,
  context,
}) => {
  await demo(page);
  const nav = page.getByRole('navigation', { name: 'Main navigation' });
  await expect(nav).not.toContainText('आज');
  await picker(page).selectOption('hi');
  await expect(nav.getByRole('button', { name: 'आज', exact: true })).toBeVisible();
  await expect
    .poll(() =>
      page.evaluate(async () => {
        return new Promise((resolve, reject) => {
          const r = indexedDB.open('munafa-offline');
          r.onsuccess = () => {
            const d = r.result;
            const q = d.transaction('cache').objectStore('cache').getAll();
            q.onsuccess = () => {
              d.close();
              resolve(q.result.some((x) => x.locale === 'hi'));
            };
            q.onerror = () => reject(q.error);
          };
          r.onerror = () => reject(r.error);
        });
      }),
    )
    .toBe(true);
  await page.reload();
  await expect(picker(page)).toHaveValue('hi');
  await picker(page).selectOption('en');
  await nav.getByRole('button', { name: 'Deliveries & Stock', exact: true }).click();
  await page.getByRole('button', { name: 'Add new bill', exact: true }).click();
  await page.getByLabel('Supplier', { exact: true }).fill('Synthetic retained supplier');
  await page.getByLabel('Invoice reference', { exact: true }).fill('DEVICE-KEEP');
  await page.getByRole('button', { name: 'Add new bill', exact: true }).click();
  await expect(page.getByRole('dialog')).toContainText('not been saved');
  await page.getByRole('button', { name: 'Continue current bill', exact: true }).click();
  await expect(page.getByLabel('Supplier', { exact: true })).toHaveValue(
    'Synthetic retained supplier',
  );
  const blockedNav = page.waitForEvent('dialog');
  const clicked = nav.getByRole('button', { name: 'More', exact: true }).click();
  (await blockedNav).dismiss();
  await clicked;
  await expect(page.getByLabel('Supplier', { exact: true })).toHaveValue(
    'Synthetic retained supplier',
  );
  await picker(page).selectOption('hi');
  await expect(page.getByLabel('सप्लायर', { exact: true })).toHaveValue(
    'Synthetic retained supplier',
  );
  await picker(page).selectOption('en');
  await page.getByRole('button', { name: 'Save purchase on device', exact: true }).click();
  await expect(page.locator('.device-sync-summary')).toContainText('1 device drafts');
  await expect(page.locator('.device-sync-summary')).not.toContainText('All changes saved');
  await page.getByRole('button', { name: 'Offline drafts', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Offline drafts', exact: true })).toBeVisible();
  await expect(page.getByText(/not a phone backup/)).toBeVisible();
  await expect(page.locator('.offline-list-card')).toContainText('DEVICE-KEEP');
  await nav.getByRole('button', { name: 'Today', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Today', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Offline drafts', exact: true }).click();
  await page.evaluate(() => navigator.serviceWorker.ready);
  await expect.poll(() => page.evaluate(() => !!navigator.serviceWorker.controller)).toBe(true);
  await context.setOffline(true);
  await page.reload();
  await expect(page.locator('.offline-list-card')).toContainText('DEVICE-KEEP');
  await context.setOffline(false);
});

test('manual photo upload keeps exact fields and replays a lost response once without AI', async ({
  page,
}) => {
  await demo(page);
  await page
    .getByRole('navigation', { name: 'Main navigation' })
    .getByRole('button', { name: 'Deliveries & Stock', exact: true })
    .click();
  await page.getByRole('button', { name: 'Add new bill', exact: true }).click();
  await page.getByLabel('Supplier', { exact: true }).fill('Synthetic photo supplier');
  await page.getByLabel('Invoice reference', { exact: true }).fill('PHOTO-RETRY');
  await page.getByLabel('Description', { exact: true }).fill('Rice');
  await page.getByLabel('Billed quantity', { exact: true }).fill('2.5');
  await page.getByRole('combobox', { name: 'Unit', exact: true }).selectOption('kg');
  await page.getByLabel('Unit price (₹)', { exact: true }).fill('80.01');
  await page.getByLabel('Invoice total (₹)', { exact: true }).fill('200.03');
  await page
    .getByLabel('Bill photo or PDF', { exact: true })
    .setInputFiles(path.resolve('evaluation/validation-v2/printed-en.png'));
  let release, committed;
  const gate = new Promise((resolve) => (release = resolve));
  const serverDone = new Promise((resolve) => (committed = resolve));
  let attempts = 0;
  await page.route('**/api/purchases/document', async (route) => {
    attempts++;
    if (attempts === 1) {
      await route.fetch();
      committed();
      await gate;
      await route.abort('failed');
    } else await route.continue();
  });
  const save = page.getByRole('button', { name: 'Save invoice draft', exact: true });
  await save.click();
  await serverDone;
  await expect(page.getByRole('button', { name: 'Add new bill', exact: true })).toBeDisabled();
  await page
    .getByRole('navigation', { name: 'Main navigation' })
    .getByRole('button', { name: 'More', exact: true })
    .click();
  await expect(page.getByRole('heading', { name: 'Review invoice', exact: true })).toBeVisible();
  await expect(
    page.getByText('Saving this bill. Please wait for confirmation.', { exact: true }),
  ).toBeVisible();
  release();
  await expect(save).toBeEnabled();
  await expect(page.getByLabel('Supplier', { exact: true })).toHaveValue(
    'Synthetic photo supplier',
  );
  const replay = page.waitForResponse(
    (r) => r.url().endsWith('/api/purchases/document') && r.status() === 201,
  );
  await save.click();
  expect((await replay).headers()['idempotency-replayed']).toBe('true');
  await expect(
    page.getByText('Draft saved. Review validation before acceptance.', { exact: true }),
  ).toBeVisible();
  const rows = await (await page.request.get('/api/purchases')).json();
  const ours = rows.filter((x) => x.draft.reference === 'PHOTO-RETRY');
  expect(ours).toHaveLength(1);
  const record = await (await page.request.get('/api/purchases/' + ours[0].id)).json();
  expect(record.documents).toHaveLength(1);
  expect(record.receipts).toHaveLength(0);
  expect(record.draft.lines[0].billed_quantity).toBe('2.5');
  expect(record.draft.lines[0].unit_price_paise).toBe(8001);
  await page.screenshot({
    path: 'artifacts/test-evidence/manual-photo-review.png',
    fullPage: true,
  });
});
