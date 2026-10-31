const { test, expect } = require('@playwright/test');
const { randomUUID } = require('node:crypto');

test('new demo opens the existing sample, preserves work and makes approval the first milestone', async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  await page.getByRole('button', { name: 'Try a demo', exact: true }).click();
  const guide = page.getByRole('region', { name: 'Sample walkthrough' });
  await expect(guide).toContainText('Review the bill and confirm what actually arrived.');
  await guide.getByRole('button', { name: 'Continue your sample invoice', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Invoice A-104', exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Confirm shortage', exact: true })).toBeDisabled();
  const rows = [
    { count: '10', unit: 'pack' },
    { count: '6', unit: 'pack' },
    { count: '24', unit: 'piece' },
  ];
  for (let i = 0; i < rows.length; i++) {
    await page
      .getByRole('spinbutton', { name: `Item ${i + 1} received quantity`, exact: true })
      .fill(rows[i].count);
    await page
      .getByRole('combobox', { name: `Item ${i + 1} billed unit`, exact: true })
      .selectOption(rows[i].unit);
    await page
      .getByRole('combobox', { name: `Item ${i + 1} received unit`, exact: true })
      .selectOption(rows[i].unit);
    await page.locator('.line-editor').nth(i).getByRole('checkbox').check();
  }
  await page.getByRole('checkbox', { name: /The delivery is complete/ }).check();
  await page.getByRole('checkbox', { name: /I verified effective unit prices/ }).check();
  await page.getByRole('button', { name: 'Save delivery review' }).click();
  await page.getByRole('button', { name: 'Confirm shortage', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Items you counted' })).toBeVisible();
  const before = await (await page.request.get('/api/cases')).json();
  const me = await (await page.request.get('/api/auth/me')).json();
  const reused = await page.request.post('/api/invoices/sample', {
    data: {},
    headers: { 'X-CSRF-Token': me.csrf, 'Idempotency-Key': randomUUID() },
  });
  expect(reused.status()).toBe(201);
  const body = await reused.json();
  expect(body.id).toBe(before[0].id);
  expect(body.history).toEqual(before[0].history);
  expect(body.sample_reused).toBe(true);
  await page.getByRole('button', { name: 'Today · आज', exact: true }).click();
  await expect(guide).toContainText('Approve the evidence — complete');
  expect(await (await page.request.get('/api/cases')).json()).toHaveLength(1);
});

test('home metrics and due/task actions open the original reviewed record on a phone', async ({
  page,
}) => {
  await page.setViewportSize({ width: 360, height: 800 });
  await page.goto('/');
  await page.getByLabel('Username', { exact: true }).fill('polish-owner');
  await page.getByLabel('Password', { exact: true }).fill('isolated-browser-test-password');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Today · आज', exact: true })).toBeVisible();
  const me = await (await page.request.get('/api/auth/me')).json();
  const date = (await (await page.request.get('/api/brief')).json()).business_date;
  async function write(path, data) {
    const r = await page.request.post('/api' + path, {
      data,
      headers: { 'X-CSRF-Token': me.csrf, 'Idempotency-Key': randomUUID() },
    });
    expect(r.status()).toBe(201);
    return r.json();
  }
  const person = await write('/records/customers', {
    name: 'Synthetic neighbour',
    reference: 'SYN-CUSTOMER',
  });
  const entry = (kind, reference, amount_paise, extra = {}) =>
    write('/records/entries', {
      kind,
      reference,
      amount_paise,
      occurred_on: date,
      note: 'Synthetic reviewed paper source',
      merchant_confirmed: true,
      ...extra,
    });
  const debt = await entry('credit_sale', 'DUE-ONE', 10000, {
    customer_id: person.id,
    due_on: date,
  });
  await entry('collection', 'PAY-ONE', 2000, {
    customer_id: person.id,
    target_id: debt.id,
    payment_channel: 'upi',
  });
  await entry('cash_sale', 'SALE-ONE', 5000);
  await entry('expense', 'EXP-ONE', 1234, { payment_channel: 'bank' });
  await write('/records/tasks', { title: 'Count the front shelf', due_on: date });
  await page.reload();
  const snapshot = page.getByRole('region', { name: 'Recorded business snapshot' });
  await expect(snapshot.getByRole('button', { name: /Today’s recorded sales/ })).toContainText(
    '₹150',
  );
  await expect(snapshot.getByRole('button', { name: /Money to Collect/ })).toContainText('₹80');
  await snapshot.getByRole('button', { name: /Today’s recorded sales/ }).click();
  const source = page.getByRole('region', { name: 'Original record' });
  await expect(source).toContainText('2 accepted source records');
  await source.getByRole('button', { name: 'Open original DUE-ONE', exact: true }).click();
  await expect(source.getByRole('heading', { name: 'DUE-ONE', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Today · आज', exact: true }).click();
  const task = page
    .getByRole('article')
    .filter({ has: page.getByRole('heading', { name: 'Count the front shelf', exact: true }) });
  await task.getByRole('button', { name: 'Review source', exact: true }).click();
  await expect(
    source.getByRole('heading', { name: 'Count the front shelf', exact: true }),
  ).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});
