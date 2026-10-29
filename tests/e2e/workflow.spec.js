const { test, expect } = require('@playwright/test');

test('merchant completes the A-104 workflow and navigates the ledger', async ({ page }) => {
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Your money, accounted for.' })).toBeVisible();
  await expect(page.getByText('₹960', { exact: true })).toBeVisible();
  await page.screenshot({ path: 'test-results/overview-desktop.png', fullPage: true });
  await page.getByRole('button', { name: 'Add an invoice', exact: true }).click();
  await page.getByRole('button', { name: 'Use sample invoice' }).click();
  await expect(page.getByRole('heading', { name: 'Invoice A-104', exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Approve evidence', exact: true })).toBeDisabled();
  const rows = [
    { count: '10', unit: 'pack' },
    { count: '6', unit: 'pack' },
    { count: '24', unit: 'piece' },
  ];
  for (let i = 0; i < 3; i++) {
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
  await expect(page.getByRole('button', { name: 'Approve evidence', exact: true })).toBeEnabled();
  await page.getByRole('button', { name: 'Approve evidence', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Confirmed delivery' })).toBeVisible();
  const downloadPromise = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Download evidence card' }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toMatch(/evidence\.png$/);
  await page.getByRole('button', { name: 'Prepare supplier message' }).click();
  await expect(page.locator('.message-preview')).toContainText(
    'Total reviewed shortage: INR 80.00',
  );
  await expect(page.getByRole('link', { name: 'Open WhatsApp' })).toHaveAttribute(
    'href',
    /^https:\/\/wa.me\//,
  );
  await page.getByRole('button', { name: 'Close dialog' }).click();
  await page
    .getByRole('checkbox', { name: 'I have sent the approved evidence to the supplier.' })
    .check();
  await page.getByRole('button', { name: 'Yes, I sent the evidence' }).click();
  await page.getByRole('button', { name: 'Record supplier promise' }).click();
  await page.getByLabel('What did the supplier say?').fill('Adjust against next bill.');
  await page.getByRole('button', { name: 'Save promise' }).click();
  await expect(page.getByText('“Adjust against next bill.”')).toBeVisible();
  await page.getByRole('button', { name: 'Verify credit / refund' }).click();
  await page.getByRole('button', { name: 'Load synthetic next-bill credit' }).click();
  await expect(
    page.getByRole('link', { name: 'Open and inspect attached evidence' }),
  ).toBeVisible();
  await page.getByRole('checkbox', { name: /I checked this proof/ }).check();
  await page.getByRole('button', { name: 'Verify and record' }).click();
  await expect(page.getByRole('heading', { name: 'Every rupee, accounted for.' })).toBeVisible();
  await page.reload();
  await page.getByRole('button', { name: 'Credit cases', exact: false }).click();
  await page.getByRole('textbox', { name: 'Search cases' }).fill('A-104');
  await expect(page.getByRole('row', { name: 'Open invoice A-104' })).toContainText('Resolved');
  await page.getByRole('button', { name: 'Suppliers', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Shree Ganesh Distributors' })).toBeVisible();
  await page.getByRole('button', { name: 'Insights', exact: true }).click();
  await expect(
    page.getByRole('heading', { name: 'Reviewed value, tracked to resolution' }),
  ).toBeVisible();
  await expect(page.getByRole('link', { name: 'Export CSV' })).toHaveAttribute(
    'href',
    '/api/export',
  );
  expect(errors).toEqual([]);
});

test('mobile overview, case detail and manual intake are usable without overflow', async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Your money, accounted for.' })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  );
  await page.screenshot({ path: 'test-results/overview-mobile.png', fullPage: true });
  await page.getByRole('button', { name: 'Credit cases', exact: false }).click();
  await page.getByRole('textbox', { name: 'Search cases' }).fill('SG-318');
  await page.getByRole('row', { name: 'Open invoice SG-318' }).click();
  await expect(page.getByRole('heading', { name: 'Invoice SG-318', exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  );
  await page.screenshot({ path: 'test-results/case-mobile.png', fullPage: true });
  await page.getByRole('button', { name: 'Back to workspace' }).click();
  await page.getByRole('button', { name: 'Add an invoice', exact: true }).click();
  await page.getByRole('button', { name: 'Enter manually' }).click();
  await page.getByLabel('Supplier name').fill('Test Wholesale');
  await page.getByLabel('Invoice reference').fill('MANUAL-01');
  await page.getByRole('textbox', { name: 'Item 1 name', exact: true }).fill('Biscuits');
  await page.getByRole('spinbutton', { name: 'Item 1 billed quantity', exact: true }).fill('10');
  await page.getByRole('spinbutton', { name: 'Item 1 unit price', exact: true }).fill('25.50');
  await page.getByRole('button', { name: 'Create draft case' }).click();
  await expect(page.getByRole('heading', { name: 'Invoice MANUAL-01', exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Approve evidence', exact: true })).toBeDisabled();
});
