const { test, expect } = require('@playwright/test');
async function login(page, name) {
  await page.goto('/');
  await page.getByLabel('Username', { exact: true }).fill(name);
  await page.getByLabel('Password', { exact: true }).fill('isolated-browser-test-password');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(
    page.getByRole('heading', { name: 'Daily business brief', exact: true }),
  ).toBeVisible();
  await page.evaluate(() => navigator.serviceWorker.ready);
  await expect.poll(() => page.evaluate(() => !!navigator.serviceWorker.controller)).toBe(true);
}
async function hub(page) {
  await page.getByRole('button', { name: 'Drafts & sync', exact: true }).first().click();
  await expect(page.getByRole('heading', { name: 'Drafts & sync', exact: true })).toBeVisible();
}
async function fillInvoice(page, reference) {
  await page.getByRole('button', { name: 'New offline invoice' }).click();
  await page.getByLabel('Supplier name', { exact: true }).fill('Synthetic Offline Wholesale');
  await page.getByLabel('Invoice reference', { exact: true }).fill(reference);
  await page.getByRole('textbox', { name: 'Item 1 name', exact: true }).fill('Rice');
  await page.getByRole('spinbutton', { name: 'Item 1 billed quantity', exact: true }).fill('1.25');
  await page.getByRole('spinbutton', { name: 'Item 1 unit price', exact: true }).fill('25.50');
  await page
    .getByLabel('Invoice / receiving notes')
    .fill('Merchant-captured synthetic offline bill');
}
async function save(page) {
  await page.getByRole('button', { name: 'Save on this device', exact: true }).click();
  await expect(
    page.getByText('Saved on this device. Queue it explicitly when ready.'),
  ).toBeVisible();
}
async function rows(page, store) {
  return page.evaluate(
    async (store) =>
      new Promise((resolve, reject) => {
        const r = indexedDB.open('munafa-offline');
        r.onsuccess = () => {
          const db = r.result;
          const q = db.transaction(store).objectStore(store).getAll();
          q.onsuccess = () => {
            db.close();
            resolve(q.result);
          };
          q.onerror = () => reject(q.error);
        };
        r.onerror = () => reject(r.error);
      }),
    store,
  );
}
async function csrfHeaders(context) {
  const cookies = await context.cookies();
  return {
    'X-CSRF-Token': cookies.find((c) => c.name === 'pbp_csrf').value,
    'Idempotency-Key': crypto.randomUUID(),
  };
}

test('offline draft survives reload; lost acceptance response retries one server event', async ({
  page,
  context,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await login(page, 'offline-owner');
  await hub(page);
  await context.setOffline(true);
  await fillInvoice(page, 'OFFLINE-ONCE');
  await save(page);
  await page.reload();
  await expect(page.getByRole('heading', { name: 'Drafts & sync', exact: true })).toBeVisible();
  await expect(page.getByText('OFFLINE-ONCE', { exact: true })).toBeVisible();
  expect((await rows(page, 'drafts'))[0].state).toBe('local_draft');
  await page.screenshot({ path: 'test-results/offline-draft-phone.png', fullPage: true });
  const sent = [];
  let replayed = false;
  await page.route('**/api/sync/operations', async (route) => {
    sent.push(route.request().postDataJSON());
    const response = await route.fetch();
    if (sent.length === 1) {
      expect(response.status()).toBe(201);
      // The server committed, but its reply arrives after the client's 12s timeout.
      await new Promise((resolve) => setTimeout(resolve, 13000));
      await route.fulfill({ response }).catch(() => {});
    } else {
      replayed = response.headers()['idempotency-replayed'] === 'true';
      await route.fulfill({ response });
    }
  });
  await context.setOffline(false);
  await expect(
    page.getByRole('heading', { name: 'Daily business brief', exact: true }),
  ).toBeVisible();
  await hub(page);
  await page.getByRole('button', { name: 'Queue for sync' }).click();
  await expect.poll(() => sent.length).toBe(1);
  await expect
    .poll(async () => (await rows(page, 'outbox'))[0]?.state, { timeout: 20000 })
    .toBe('pending_sync');
  await page.reload();
  await expect(
    page.getByRole('heading', { name: 'Daily business brief', exact: true }),
  ).toBeVisible();
  await hub(page);
  await expect
    .poll(
      async () => {
        const retry = page.getByRole('button', { name: 'Sync now', exact: true });
        if (await retry.isEnabled()) await retry.click();
        return (await rows(page, 'outbox'))[0]?.state;
      },
      { timeout: 25000 },
    )
    .toBe('synced');
  expect(sent.length).toBe(2);
  expect(sent[0]).toEqual(sent[1]);
  expect(replayed).toBe(true);
  const cases = await (await page.request.get('/api/cases')).json();
  expect(cases.filter((c) => c.invoice.reference === 'OFFLINE-ONCE')).toHaveLength(1);
  expect(cases[0].history).toHaveLength(1);
});

test('attachment capture survives reload and response loss without duplicate upload', async ({
  page,
  context,
}) => {
  await login(page, 'offline-attachment');
  await hub(page);
  await context.setOffline(true);
  await fillInvoice(page, 'OFFLINE-FILE');
  const bytes = Buffer.from(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAFgAI/ScLbtAAAAABJRU5ErkJggg==',
    'base64',
  );
  await page
    .getByLabel('Capture invoice attachment')
    .setInputFiles({ name: 'synthetic.png', mimeType: 'image/png', buffer: bytes });
  await save(page);
  await page.reload();
  expect(await rows(page, 'attachments')).toHaveLength(1);
  const uploads = [];
  await page.route('**/api/sync/operations', async (route) => {
    const body = route.request().postDataJSON();
    const response = await route.fetch();
    if (body.operation_type === 'attachment_upload') {
      uploads.push(body);
      if (uploads.length === 1) {
        await route.abort('failed');
        return;
      }
    }
    await route.fulfill({ response });
  });
  await context.setOffline(false);
  await expect(
    page.getByRole('heading', { name: 'Daily business brief', exact: true }),
  ).toBeVisible();
  await hub(page);
  await page.getByRole('button', { name: 'Queue for sync' }).click();
  await expect
    .poll(
      async () => {
        const button = page.getByRole('button', { name: 'Sync now', exact: true });
        if (await button.isEnabled()) await button.click();
        return (await rows(page, 'outbox')).filter((o) => o.state === 'synced').length;
      },
      { timeout: 30000 },
    )
    .toBe(2);
  expect(uploads).toHaveLength(2);
  expect(uploads[0]).toEqual(uploads[1]);
  const cases = await (await page.request.get('/api/cases')).json();
  expect(cases).toHaveLength(1);
  expect(cases[0].version).toBe(2);
  const file = await page.request.get('/api/attachments/' + cases[0].attachment_id);
  expect(await file.body()).toEqual(bytes);
  expect(await rows(page, 'attachments')).toHaveLength(0);
});

test('quota failure keeps the open editor and the previously saved draft', async ({ page }) => {
  await login(page, 'offline-quota');
  await hub(page);
  await fillInvoice(page, 'SAVED-BEFORE-QUOTA');
  await save(page);
  await page.getByRole('button', { name: 'Edit draft', exact: true }).click();
  await page.getByLabel('Invoice reference', { exact: true }).fill('NOT-SAVED');
  await page.evaluate(() => {
    window.originalIDBPut = IDBObjectStore.prototype.put;
    IDBObjectStore.prototype.put = function (...args) {
      if (this.name === 'drafts')
        throw new DOMException('Injected full storage', 'QuotaExceededError');
      return window.originalIDBPut.apply(this, args);
    };
  });
  await page.getByRole('button', { name: 'Save on this device', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('Device storage is full');
  await expect(page.getByLabel('Invoice reference', { exact: true })).toHaveValue('NOT-SAVED');
  expect((await rows(page, 'drafts'))[0].payload.invoice.reference).toBe('SAVED-BEFORE-QUOTA');
  await page.evaluate(() => {
    IDBObjectStore.prototype.put = window.originalIDBPut;
  });
});

test('logout and account switch clear previous private drafts', async ({ page, context }) => {
  await login(page, 'offline-second');
  await hub(page);
  await fillInvoice(page, 'PRIVATE-PREVIOUS');
  await save(page);
  await page.getByRole('button', { name: 'Back to business' }).click();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole('button', { name: 'More', exact: true }).click();
  page.once('dialog', (d) => d.accept());
  await page.getByRole('button', { name: 'Sign out', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Sign in', exact: true })).toBeVisible();
  expect(await rows(page, 'drafts')).toHaveLength(0);
  expect(await rows(page, 'outbox')).toHaveLength(0);
  await login(page, 'offline-quota');
  await hub(page);
  await expect(page.getByText('PRIVATE-PREVIOUS', { exact: true })).toHaveCount(0);
});

test('expired auth retains queued draft and same-account sign-in resumes', async ({
  page,
  context,
}) => {
  await login(page, 'offline-expired');
  await hub(page);
  await context.setOffline(true);
  await fillInvoice(page, 'AUTH-RETAIN');
  await save(page);
  await page.getByRole('button', { name: 'Queue for sync' }).click();
  await context.clearCookies();
  await context.setOffline(false);
  await expect(page.getByRole('button', { name: 'Sign in', exact: true })).toBeVisible();
  expect((await rows(page, 'drafts'))[0].payload.invoice.reference).toBe('AUTH-RETAIN');
  await login(page, 'offline-expired');
  await hub(page);
  await expect.poll(async () => (await rows(page, 'outbox'))[0]?.state).toBe('synced');
});

test('stale receiving becomes a human-reviewed conflict without overwriting server counts', async ({
  page,
  context,
}) => {
  await login(page, 'offline-conflict');
  const c = await (
    await page.request.post('/api/invoices/sample', { headers: await csrfHeaders(context) })
  ).json();
  await page.reload();
  await expect(
    page.getByRole('heading', { name: 'Daily business brief', exact: true }),
  ).toBeVisible();
  await hub(page);
  await context.setOffline(true);
  await page.getByLabel('Choose invoice for offline receiving').selectOption(c.id);
  await page.getByLabel('Actually received', { exact: true }).first().fill('9');
  await save(page);
  await page.getByRole('button', { name: 'Queue for sync' }).click();
  const invoice = c.invoice;
  invoice.lines[0].received = 11;
  const response = await page.request.patch(`/api/cases/${c.id}/review`, {
    headers: await csrfHeaders(context),
    data: { version: 1, invoice, delivery_complete: false, pricing_confirmed: false },
  });
  expect(response.status()).toBe(200);
  await context.setOffline(false);
  await expect(page.getByText('Connected · server acceptance is required')).toBeVisible();
  await expect.poll(async () => (await rows(page, 'outbox'))[0]?.state).toBe('conflict');
  await page.getByRole('button', { name: 'Review / revise draft' }).click();
  await expect(page.getByRole('heading', { name: 'Review receiving conflict' })).toBeVisible();
  await expect(page.getByText(/Your saved base: v1. Server: v2/)).toBeVisible();
  const latest = await (await page.request.get('/api/cases/' + c.id)).json();
  expect(latest.invoice.lines[0].received).toBe(11);
  expect(latest.version).toBe(2);
});
