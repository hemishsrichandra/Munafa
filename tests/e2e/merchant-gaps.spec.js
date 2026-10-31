const { test, expect } = require('@playwright/test');
const { randomUUID } = require('node:crypto');

test('source-backed overdue, payment chips and expiry radar are accessible on a phone', async ({
  page,
}) => {
  await page.setViewportSize({ width: 360, height: 800 });
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto('/');
  await page.getByRole('button', { name: 'Try a demo', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Today', exact: true })).toBeVisible();
  const me = await (await page.request.get('/api/auth/me')).json();
  const brief = await (await page.request.get('/api/brief')).json();
  const date = brief.business_date;
  const shifted = (days) => {
    const d = new Date(date + 'T12:00:00Z');
    d.setUTCDate(d.getUTCDate() + days);
    return d.toISOString().slice(0, 10);
  };
  async function write(path, data) {
    const r = await page.request.post('/api' + path, {
      data,
      headers: { 'X-CSRF-Token': me.csrf, 'Idempotency-Key': randomUUID() },
    });
    expect(r.ok(), await r.text()).toBe(true);
    return r.json();
  }
  const customer = await write('/records/customers', {
    name: 'Synthetic overdue customer',
    reference: 'GAP-C',
    phone: '919876543210',
  });
  await write('/records/entries', {
    kind: 'opening_due',
    customer_id: customer.id,
    reference: 'GAP-DUE',
    amount_paise: 65005,
    occurred_on: shifted(-8),
    due_on: shifted(-7),
    note: 'Synthetic checked ledger',
    merchant_confirmed: true,
  });
  const product = await write('/products', {
    code: 'GAP-SKU',
    name: 'Synthetic expiry item',
    unit: 'kg',
    expiry_tracking: true,
  });
  async function accept(kind, entity, version, payload = {}) {
    let action = await write('/commerce/proposals', {
      action_type: kind,
      entity_id: entity,
      expected_version: version,
      payload,
    });
    action = await write(`/actions/${action.id}/approve`, {
      version: action.version,
      payload_digest: action.payload_digest,
    });
    return write(`/actions/${action.id}/execute`, { version: action.version });
  }
  const purchase = await write('/purchases/manual', {
    supplier: 'Synthetic supplier',
    reference: 'GAP-BILL',
    date,
    lines: [
      {
        description: product.name,
        product_id: product.id,
        billed_quantity: '2.5',
        unit: 'kg',
        unit_price_paise: 8001,
        effective_price_paise: 8001,
      },
    ],
    tax_paise: 0,
    discount_paise: 0,
    rounding_paise: -1,
    total_paise: 20002,
  });
  await accept('accept_purchase', purchase.id, purchase.version);
  await accept('inventory_movement', product.id, 0, {
    product_id: product.id,
    expected_stock_version: 0,
    kind: 'count',
    quantity: '2.5',
    unit: 'kg',
    reference: 'GAP-BATCH',
    occurred_on: date,
    expiry_date: shifted(5),
    batch_reference: 'SYN-BATCH',
    reason: 'Synthetic physical stock count',
  });
  await page.reload();
  const attention = page.getByRole('region', { name: 'Expiry attention', exact: true });
  await expect(attention).toContainText('1 batches due within 7 days');
  const reminder = page.getByRole('button', {
    name: 'Review reminder for Synthetic overdue customer',
  });
  await reminder.click();
  const dialog = page.getByRole('dialog');
  await expect(dialog).toContainText('650.05');
  await expect(dialog.getByRole('link', { name: 'Open WhatsApp' })).not.toHaveAttribute(
    'href',
    /./,
  );
  await dialog.getByRole('checkbox').check();
  await expect(dialog.getByRole('link', { name: 'Open WhatsApp' })).toHaveAttribute(
    'href',
    /^https:\/\/wa.me\/919876543210/,
  );
  await dialog.getByRole('button', { name: 'Close dialog' }).click();
  await page.getByRole('button', { name: 'Open expiry radar', exact: true }).click();
  const radar = page.getByRole('region', { name: 'Expiry radar', exact: true });
  await expect(radar).toContainText('Synthetic expiry item');
  await expect(radar).toContainText('₹200.03');
  await expect(radar).toContainText('₹40.01');
  await radar.getByRole('button', { name: 'Review clearance message' }).click();
  await expect(dialog.getByRole('link', { name: 'Open WhatsApp' })).not.toHaveAttribute(
    'href',
    /./,
  );
  await dialog.getByRole('checkbox').check();
  await expect(dialog.getByRole('link', { name: 'Open WhatsApp' })).toHaveAttribute(
    'href',
    /40.01/,
  );
  await dialog.getByRole('button', { name: 'Close dialog' }).click();
  await page
    .getByRole('navigation', { name: 'Main navigation' })
    .getByRole('button', { name: 'Customer Khata', exact: true })
    .click();
  await expect(page.locator('.overdue-badge').first()).toContainText('7 days overdue');
  await page.getByRole('button', { name: 'View account history', exact: true }).click();
  await expect(page.getByRole('button', { name: /Open original GAP-DUE/ })).toContainText(
    '7 days late',
  );
  await page.getByRole('button', { name: 'Received payment (+)', exact: true }).click();
  await page.getByRole('button', { name: 'Full balance: ₹650.05', exact: true }).click();
  await expect(page.getByLabel('Recorded amount (₹)', { exact: true })).toHaveValue('650.05');
  await expect(page.getByRole('checkbox', { name: /I checked this entry/ })).not.toBeChecked();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  expect(errors).toEqual([]);
});
