const { test, expect } = require('@playwright/test');
async function login(page, name) {
  await page.goto('/');
  await page.getByLabel('Username', { exact: true }).fill(name);
  await page.getByLabel('Password', { exact: true }).fill('isolated-browser-test-password');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Daily business brief' })).toBeVisible();
  await page.getByRole('button', { name: 'More', exact: true }).click();
  await page.getByRole('button', { name: 'Daily records', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Customer accounts', exact: true })).toBeVisible();
}
async function record(page, kind, ref, amount, customer = false) {
  await page.getByRole('button', { name: 'Sales & expenses', exact: true }).click();
  await page.getByRole('combobox', { name: 'Record type', exact: true }).selectOption(kind);
  if (customer)
    await page
      .getByRole('combobox', { name: 'Customer', exact: true })
      .selectOption({ label: 'Ravi · MAN-RAVI' });
  await page.getByLabel('Unique record reference', { exact: true }).fill(ref);
  await page.getByLabel('Recorded amount (₹)', { exact: true }).fill(amount);
  await page.getByLabel('Source / reason', { exact: true }).fill('Checked synthetic notebook');
  await page
    .getByText("I checked this entry's type, amount, date and allocation against my source.", {
      exact: true,
    })
    .click();
}

test('manual customer, allocation, cash, tasks and consented marketing work without external integration', async ({
  page,
}) => {
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await page.setViewportSize({ width: 390, height: 844 });
  await login(page, 'records-owner');
  await page.getByLabel('Customer name', { exact: true }).fill('Ravi');
  await page.getByLabel('Customer reference', { exact: true }).fill('MAN-RAVI');
  await page
    .getByText('Customer agreed to being selected in local promotional drafts', { exact: true })
    .click();
  await page
    .getByLabel('Consent or withdrawal note', { exact: true })
    .fill('Synthetic customer agreed on this date');
  await page.getByRole('button', { name: 'Save customer', exact: true }).click();
  await expect(page.getByText('Customer recorded.', { exact: true })).toBeVisible();
  await record(page, 'credit_sale', 'SALE-1', '10.01', true);
  await page.getByRole('button', { name: 'Save reviewed entry', exact: true }).click();
  await expect(page.getByText(/Reviewed record saved/)).toBeVisible();
  await page.getByRole('button', { name: 'Customers', exact: true }).click();
  await expect(page.getByText('₹10.01 pending', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Prepare payment reminder', exact: true }).click();
  await expect(page.getByText(/INR 10.01 pending/)).toBeVisible();
  await record(page, 'collection', 'COLL-1', '2.01', true);
  await page
    .getByRole('combobox', { name: 'Allocate payment to', exact: true })
    .selectOption({ label: 'SALE-1 · ₹10.01 remaining' });
  await page
    .getByText("I checked this entry's type, amount, date and allocation against my source.", {
      exact: true,
    })
    .click();
  await page.getByRole('button', { name: 'Save reviewed entry', exact: true }).click();
  await expect(page.getByText(/Reviewed record saved/)).toBeVisible();
  await page.getByRole('button', { name: 'Customers', exact: true }).click();
  await expect(page.getByText('₹8 pending', { exact: true })).toBeVisible();
  await record(page, 'opening_cash', 'OPEN-1', '100.00');
  await page.getByRole('button', { name: 'Save reviewed entry', exact: true }).click();
  await expect(page.getByText(/Reviewed record saved/)).toBeVisible();
  await page.getByRole('button', { name: 'Cash outlook', exact: true }).click();
  await expect(page.getByRole('paragraph').filter({ hasText: 'Recorded cash:' })).toHaveText(
    'Recorded cash: ₹102.01',
  );
  await record(page, 'expense', 'BANK-EXP', '1.00');
  await page.getByRole('combobox', { name: 'Payment channel', exact: true }).selectOption('bank');
  await page
    .getByText("I checked this entry's type, amount, date and allocation against my source.", {
      exact: true,
    })
    .click();
  await page.getByRole('button', { name: 'Save reviewed entry', exact: true }).click();
  await expect(page.getByText(/Reviewed record saved/)).toBeVisible();
  await page.getByRole('button', { name: 'Cash outlook', exact: true }).click();
  await expect(page.getByRole('paragraph').filter({ hasText: 'Recorded cash:' })).toHaveText(
    'Recorded cash: ₹102.01',
  );
  await page.getByRole('button', { name: 'Tasks', exact: true }).click();
  await page.getByLabel('Task title', { exact: true }).fill('Check opening stock');
  await page.getByRole('button', { name: 'Save task', exact: true }).click();
  await expect(
    page.getByRole('heading', { name: 'Check opening stock', exact: true }),
  ).toBeVisible();
  await page.getByRole('button', { name: 'Mark task done', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Reopen task', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Marketing drafts', exact: true }).click();
  await page.getByLabel('Campaign title', { exact: true }).fill('Local rice offer');
  await page.getByLabel('Promotion text', { exact: true }).fill('Synthetic rice offer for review');
  await page.getByText('Ravi · 1 recorded sales', { exact: true }).click();
  await page
    .getByText('I reviewed this text and the selected recipients for a local draft.', {
      exact: true,
    })
    .click();
  await page.getByRole('button', { name: 'Save campaign draft', exact: true }).click();
  await expect(
    page.getByText('Local campaign draft saved. Nothing sent.', { exact: true }),
  ).toBeVisible();
  expect(errors).toEqual([]);
  for (const width of [320, 390, 844]) {
    await page.setViewportSize({ width, height: 844 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
      true,
    );
  }
  await page.screenshot({
    path: 'artifacts/test-evidence/manual-records-marketing.png',
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole('button', { name: 'Home', exact: true }).click();
  const snapshot = page.getByRole('region', { name: 'Recorded business snapshot' });
  await expect(snapshot.getByText('₹10.01', { exact: true })).toBeVisible();
  await expect(snapshot.getByText('₹8.00', { exact: true })).toBeVisible();
  await expect(snapshot.getByText('₹1.00', { exact: true })).toBeVisible();
  await expect(snapshot.getByText(/Cash drawer: ₹102.01/)).toBeVisible();
  await expect(snapshot.getByText('0', { exact: true })).toBeVisible();
  for (const width of [320, 390, 844]) {
    await page.setViewportSize({ width, height: 844 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
      true,
    );
  }
  await snapshot.getByRole('button', { name: 'Open daily records' }).click();
  await expect(page.getByRole('heading', { name: 'Customer accounts', exact: true })).toBeVisible();
});

test('manual cash draft survives offline reload and reaches ledger once after queued review', async ({
  page,
  context,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await login(page, 'records-offline');
  await record(page, 'cash_sale', 'OFF-MANUAL', '1.01');
  await context.setOffline(true);
  await page.getByRole('button', { name: 'Save record on device', exact: true }).click();
  await expect(page.getByText(/Saved on this device. Review and queue/)).toBeVisible();
  await page.reload();
  await expect(page.getByRole('heading', { name: 'Drafts & sync', exact: true })).toBeVisible();
  await expect(page.getByText('business_entry: OFF-MANUAL', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Queue for sync', exact: true }).click();
  await context.setOffline(false);
  await expect
    .poll(async () =>
      page.evaluate(async () => {
        const r = await fetch('/api/records/summary');
        return r.ok ? (await r.json()).sales_paise : null;
      }),
    )
    .toBe(101);
  await page.reload();
  await expect
    .poll(async () =>
      page.evaluate(async () => {
        const r = await fetch('/api/records/summary');
        return r.ok ? (await r.json()).sales_paise : null;
      }),
    )
    .toBe(101);
});
