import test, { beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { indexedDB, IDBKeyRange, IDBObjectStore } from 'fake-indexeddb';
import { webcrypto } from 'node:crypto';
import * as db from '../src/offline/db.js';
import { syncBatch, retryDelay, failureState } from '../src/offline/sync.js';
Object.assign(globalThis, { indexedDB, IDBKeyRange });
if (!globalThis.crypto) Object.defineProperty(globalThis, 'crypto', { value: webcrypto });
const session = {
  user_id: 'user-a',
  role: 'owner',
  permissions: ['read', 'write'],
  store: { id: 'store-a', name: 'Test synthetic store', demo: true, timezone: 'Asia/Kolkata' },
};
let scope;
const draft = () => ({
  id: crypto.randomUUID(),
  kind: 'invoice',
  payload: {
    invoice: { supplier: 'Synthetic', reference: 'OFF-1', date: '2026-10-30', lines: [] },
  },
});
const reset = () =>
  new Promise((resolve, reject) => {
    db.closeDB();
    const r = indexedDB.deleteDatabase(db.DB_NAME);
    r.onsuccess = resolve;
    r.onerror = () => reject(r.error);
  });
beforeEach(async () => {
  await reset();
  scope = await db.activate(session);
});
afterEach(reset);

test('commerce drafts preserve exact operation types and stock version zero', async () => {
  for (const [kind, type] of [
    ['purchase', 'purchase_create'],
    ['purchase_receiving', 'purchase_receiving_capture'],
    ['inventory_movement', 'inventory_movement'],
  ]) {
    const d = {
      id: crypto.randomUUID(),
      kind,
      entity_id: kind === 'purchase' ? null : 'source',
      expected_version: kind === 'purchase' ? null : 0,
      payload:
        kind === 'purchase'
          ? { draft: { supplier: 'Shop', reference: 'B5' } }
          : { quantity: '2.500001' },
    };
    await db.saveDraft(scope, d);
    const id = await db.queueDraft(scope, d.id);
    const row = await db.getRecord('outbox', id, scope);
    assert.equal(row.operation_type, type);
    assert.equal(row.expected_version, d.expected_version);
  }
});

test('purchase evidence queues with checksum and a dependent document upload', async () => {
  const blob = new Blob(['%PDF-1.4\nSynthetic purchase'], { type: 'application/pdf' });
  blob.name = 'purchase.pdf';
  const d = {
    id: crypto.randomUUID(),
    kind: 'purchase',
    payload: { draft: { supplier: 'Synthetic', reference: 'B5' } },
  };
  await db.saveDraft(scope, d, blob);
  await db.queueDraft(scope, d.id);
  const rows = await db.list('outbox', scope);
  const create = rows.find((r) => r.operation_type === 'purchase_create');
  const upload = rows.find((r) => r.operation_type === 'purchase_document_upload');
  assert.equal(create.payload.document.sha256.length, 64);
  assert.deepEqual(upload.dependency_ids, [create.id]);
  assert.equal(upload.entity_ref, create.id);
});

test('minimal scoped cache and identity exclude credentials and history', async () => {
  await db.activate({ ...session, csrf: 'never-persist', session_token: 'secret' });
  await db.cacheCases(scope, [
    {
      id: 'c1',
      version: 1,
      status: 'review',
      invoice: { reference: 'A' },
      history: ['private-audit'],
    },
  ]);
  assert.equal((await db.context()).session.csrf, undefined);
  assert.equal((await db.list('cache', scope))[0].cases[0].history, undefined);
  await assert.rejects(db.list('cache', 'another-store'));
});
test('saved draft and immutable queue survive reopen; concurrent claims do not duplicate', async () => {
  const d = draft();
  await db.saveDraft(scope, d);
  const op = await db.queueDraft(scope, d.id);
  db.closeDB();
  assert.equal((await db.list('drafts', scope))[0].state, 'pending_sync');
  await assert.rejects(db.saveDraft(scope, d), /frozen/);
  const claims = await Promise.all([
    db.claimOperation(scope, op, 'tab1'),
    db.claimOperation(scope, op, 'tab2'),
  ]);
  assert.equal(claims.filter(Boolean).length, 1);
  assert.throws(() => db.transition(claims.find(Boolean), 'local_draft'), /Invalid/);
  await db.updateOperation(scope, op, 'synced', { result: { entity_id: 'c1', entity_version: 1 } });
  assert.equal((await db.list('drafts', scope))[0].state, 'synced');
});
test('quota failure aborts write and preserves the prior saved draft', async () => {
  const d = draft();
  await db.saveDraft(scope, d);
  const put = IDBObjectStore.prototype.put;
  IDBObjectStore.prototype.put = function (...args) {
    if (this.name === 'drafts') throw new DOMException('full', 'QuotaExceededError');
    return put.apply(this, args);
  };
  try {
    await assert.rejects(
      db.saveDraft(scope, { ...d, payload: { invoice: { reference: 'unsaved' } } }),
      { name: 'QuotaExceededError' },
    );
  } finally {
    IDBObjectStore.prototype.put = put;
  }
  assert.equal((await db.list('drafts', scope))[0].payload.invoice.reference, 'OFF-1');
});
test('account, store or role switch purges previous context; logout clears blobs and outbox', async () => {
  await db.saveDraft(scope, draft());
  const other = await db.activate({ ...session, store: { ...session.store, id: 'store-b' } });
  assert.deepEqual(await db.list('drafts', other), []);
  await assert.rejects(db.list('drafts', scope));
  await db.saveDraft(other, draft());
  const changed = await db.activate({ ...session, role: 'viewer', permissions: ['read'] });
  assert.deepEqual(await db.list('drafts', changed), []);
  await db.clearPrivate(true);
  assert.equal(await db.logoutPending(), true);
  assert.equal(await db.context(), undefined);
});
test('timeout replays the exact operation and receipt; failed states and retry backoff are bounded', async () => {
  const d = draft();
  await db.saveDraft(scope, d);
  await db.queueDraft(scope, d.id);
  let sent = [],
    accepted = 0;
  const api = async (path, options) => {
    if (path === '/auth/me') return session;
    sent.push(options.body);
    if (sent.length === 1) {
      accepted++;
      throw new Error('Response lost after acceptance');
    }
    return { operation_id: options.body.operation_id, entity_id: 'c1', entity_version: 1 };
  };
  await syncBatch({ scope, api, online: () => true });
  const row = (await db.list('outbox', scope))[0];
  assert.equal(row.state, 'pending_sync');
  await db.updateOperation(scope, row.id, null, { next_attempt_at: 0 });
  db.closeDB();
  await syncBatch({ scope, api, online: () => true });
  assert.deepEqual(sent[0], sent[1]);
  assert.equal(accepted, 1);
  assert.equal((await db.list('outbox', scope))[0].state, 'synced');
  assert.equal(failureState({ status: 409 }, 1), 'conflict');
  assert.equal(failureState({ status: 422 }, 1), 'needs_attention');
  assert.equal(failureState({}, 5), 'needs_attention');
  assert.equal(
    retryDelay(1, () => 0),
    750,
  );
  assert.ok(retryDelay(10, () => 1) <= 75000);
});
test('dependency executes only after parent; stale version and auth failure retain drafts', async () => {
  const d = { ...draft(), kind: 'receiving', entity_id: 'c1', expected_version: 2 };
  await db.saveDraft(scope, d);
  await db.queueDraft(scope, d.id);
  const api = async (path) => {
    if (path === '/auth/me') return session;
    throw Object.assign(new Error('Changed in another tab'), { status: 409 });
  };
  await syncBatch({ scope, api, online: () => true });
  assert.equal((await db.list('outbox', scope))[0].state, 'conflict');
  assert.equal((await db.list('drafts', scope)).length, 1);
  await assert.rejects(
    syncBatch({
      scope,
      online: () => true,
      api: async () => {
        throw Object.assign(new Error('expired'), { status: 401 });
      },
    }),
    { status: 401 },
  );
  assert.equal((await db.list('drafts', scope)).length, 1);
});
test('interrupted syncing lease recovers only after expiry', async () => {
  const d = draft();
  await db.saveDraft(scope, d);
  const id = await db.queueDraft(scope, d.id);
  const first = await db.claimOperation(scope, id, 'tab1', 100);
  assert.equal(await db.claimOperation(scope, id, 'tab2', 101), null);
  const retry = await db.claimOperation(scope, id, 'tab2', first.lease_until + 1);
  assert.equal(retry.operation_id, first.operation_id);
  assert.equal(retry.attempts, 2);
});
test('unknown future database schema is preserved instead of reset', async () => {
  db.closeDB();
  await new Promise((resolve, reject) => {
    const r = indexedDB.open(db.DB_NAME, 2);
    r.onsuccess = () => {
      r.result.close();
      resolve();
    };
    r.onerror = () => reject(r.error);
  });
  await assert.rejects(db.openDB(), { name: 'VersionError' });
});

test('queued payload cannot be revised and retained drafts are not age-deleted', async () => {
  const d = draft();
  await db.saveDraft(scope, d);
  const id = await db.queueDraft(scope, d.id);
  await assert.rejects(
    db.updateOperation(scope, id, null, { payload: { changed: true } }),
    /immutable/,
  );
  await db.transaction(['drafts'], async (stores) => {
    const row = await db.requestValue(stores.drafts.get(d.id));
    stores.drafts.put({ ...row, updated_at: Date.now() - 40 * 86400000 });
  });
  await db.cleanup(scope);
  assert.equal((await db.list('drafts', scope)).length, 1);
});
test('failed validation is retained, automatic retries stop, and offline batches send nothing', async () => {
  const d = draft();
  await db.saveDraft(scope, d);
  const id = await db.queueDraft(scope, d.id);
  let calls = 0;
  await syncBatch({
    scope,
    online: () => false,
    api: async () => {
      calls++;
    },
  });
  assert.equal(calls, 0);
  await db.updateOperation(scope, id, null, { attempts: 5 });
  await syncBatch({
    scope,
    online: () => true,
    api: async (path) => {
      assert.equal(path, '/auth/me');
      return session;
    },
  });
  assert.equal((await db.list('outbox', scope))[0].state, 'needs_attention');
  assert.equal((await db.list('drafts', scope)).length, 1);
});
test('attachment blobs and dependency operations persist atomically and clean only on full acceptance', async () => {
  const blob = new Blob(['%PDF-1.4\nSynthetic unit-test invoice'], { type: 'application/pdf' });
  blob.name = 'synthetic.pdf';
  const d = draft();
  await db.saveDraft(scope, d, blob);
  await db.queueDraft(scope, d.id);
  db.closeDB();
  const rows = await db.list('outbox', scope),
    attachment = rows.find((o) => o.operation_type === 'attachment_upload'),
    parent = rows.find((o) => o.operation_type === 'invoice_create');
  assert.deepEqual(attachment.dependency_ids, [parent.id]);
  assert.equal((await db.list('attachments', scope))[0].blob.size, blob.size);
  await db.claimOperation(scope, parent.id, 'tab');
  await db.updateOperation(scope, parent.id, 'synced', {
    result: { entity_id: 'c', entity_version: 1 },
  });
  assert.equal((await db.list('drafts', scope))[0].state, 'pending_sync');
  assert.equal((await db.list('attachments', scope)).length, 1);
  await db.claimOperation(scope, attachment.id, 'tab');
  await db.updateOperation(scope, attachment.id, 'synced', {
    result: { entity_id: 'c', entity_version: 2 },
  });
  assert.equal((await db.list('attachments', scope)).length, 0);
  assert.ok((await db.list('drafts', scope))[0].synced_at);
});

test('a resumed stale tab cannot complete or fail another tab’s recovered attempt', async () => {
  const d = draft();
  await db.saveDraft(scope, d);
  const id = await db.queueDraft(scope, d.id);
  const first = await db.claimOperation(scope, id, 'old-tab', 100);
  await db.claimOperation(scope, id, 'new-tab', first.lease_until + 1);
  await db.updateOperation(
    scope,
    id,
    'synced',
    { result: { entity_id: 'c', entity_version: 1 } },
    'old-tab',
  );
  assert.equal((await db.list('outbox', scope))[0].state, 'syncing');
  await db.updateOperation(
    scope,
    id,
    'synced',
    { result: { entity_id: 'c', entity_version: 1 } },
    'new-tab',
  );
  await db.updateOperation(scope, id, 'pending_sync', { error: 'late timeout' }, 'old-tab');
  assert.equal((await db.list('outbox', scope))[0].state, 'synced');
});

test('reviewed manual business entry queues exactly and cannot queue without confirmation', async () => {
  const d = {
    id: crypto.randomUUID(),
    kind: 'business_entry',
    payload: {
      kind: 'cash_sale',
      reference: 'OFF-CASH',
      amount_paise: 101,
      merchant_confirmed: false,
    },
  };
  await db.saveDraft(scope, d);
  await assert.rejects(db.queueDraft(scope, d.id), /confirm/);
  d.payload.merchant_confirmed = true;
  await db.saveDraft(scope, d);
  const id = await db.queueDraft(scope, d.id);
  const row = await db.getRecord('outbox', id, scope);
  assert.equal(row.operation_type, 'business_entry_create');
  assert.equal(row.payload.amount_paise, 101);
  db.closeDB();
  assert.equal((await db.getRecord('outbox', id, scope)).payload.reference, 'OFF-CASH');
});
