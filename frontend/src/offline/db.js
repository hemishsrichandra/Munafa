// IndexedDB only. Never store a token, password, CSRF value or full audit history here.
export const DB_NAME = 'munafa-offline';
export const DB_VERSION = 1;
export const PRIVATE_STORES = ['cache', 'drafts', 'attachments', 'outbox', 'status'];
export const STATES = [
  'local_draft',
  'pending_sync',
  'syncing',
  'synced',
  'needs_attention',
  'conflict',
];
const moves = {
  local_draft: ['pending_sync'],
  pending_sync: ['syncing', 'needs_attention'],
  syncing: ['synced', 'pending_sync', 'needs_attention', 'conflict'],
  needs_attention: ['pending_sync'],
  conflict: [],
  synced: [],
};
let connection;
const listeners = new Set();
const channel =
  typeof window !== 'undefined' && typeof BroadcastChannel !== 'undefined'
    ? new BroadcastChannel('munafa-offline')
    : null;
channel?.addEventListener('message', () => listeners.forEach((fn) => fn()));
export const subscribe = (fn) => {
  listeners.add(fn);
  return () => listeners.delete(fn);
};
function changed() {
  listeners.forEach((fn) => fn());
  channel?.postMessage('changed');
}
export function storageMessage(error) {
  if (error?.name === 'QuotaExceededError')
    return 'Device storage is full. Nothing new was saved. Keep this form open, free space, then retry.';
  if (error?.name === 'VersionError')
    return 'This app is older than the saved data. Update the app; do not clear site storage.';
  return (
    error?.message ||
    'Device storage is unavailable. Keep your draft open and retry. Do not clear site storage.'
  );
}
export function openDB() {
  if (connection) return Promise.resolve(connection);
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onupgradeneeded = () => {
      const db = request.result;
      db.createObjectStore('meta', { keyPath: 'key' });
      for (const name of PRIVATE_STORES) {
        const store = db.createObjectStore(name, { keyPath: 'id' });
        store.createIndex('scope', 'scope');
      }
    };
    request.onerror = () => reject(request.error);
    request.onblocked = () =>
      reject(
        new Error(
          'Close other Munafa tabs to finish the storage upgrade. Existing drafts have not been deleted.',
        ),
      );
    request.onsuccess = () => {
      const db = request.result;
      if (
        db.objectStoreNames.length !== PRIVATE_STORES.length + 1 ||
        [...PRIVATE_STORES, 'meta'].some((name) => !db.objectStoreNames.contains(name))
      ) {
        db.close();
        reject(
          new Error(
            'Device data schema needs attention. Export any open draft; do not reset storage.',
          ),
        );
        return;
      }
      connection = db;
      db.onversionchange = () => {
        db.close();
        connection = null;
        changed();
      };
      db.onclose = () => {
        connection = null;
      };
      resolve(db);
    };
  });
}
export function closeDB() {
  connection?.close();
  connection = null;
}
// All reads and transitions use real transaction completion, not request success.
export async function transaction(names, fn, mode = 'readwrite') {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(names, mode);
    let result, failure;
    tx.oncomplete = () => {
      if (mode === 'readwrite') changed();
      resolve(result);
    };
    tx.onabort = () => reject(failure || tx.error || new Error('Device write was not committed.'));
    tx.onerror = () => {};
    const stores = Object.fromEntries(names.map((name) => [name, tx.objectStore(name)]));
    Promise.resolve()
      .then(() => fn(stores))
      .then((value) => {
        result = value;
      })
      .catch((error) => {
        failure = error;
        try {
          tx.abort();
        } catch {
          reject(error);
        }
      });
  });
}
export const requestValue = (request) =>
  new Promise((resolve, reject) => {
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
export const scopeOf = (session) =>
  JSON.stringify([
    session.user_id,
    session.store.id,
    session.role,
    [...session.permissions].sort(),
  ]);
const identity = (session) => ({
  user_id: session.user_id,
  store: session.store,
  role: session.role,
  permissions: session.permissions,
});
export const context = () =>
  transaction(['meta'], async (s) => requestValue(s.meta.get('context')), 'readonly');
export const logoutPending = () =>
  transaction(
    ['meta'],
    async (s) => !!(await requestValue(s.meta.get('logout_required')))?.value,
    'readonly',
  );
export async function activate(session) {
  if (!session.user_id || !session.store?.id)
    throw new Error('Verified user and store are required for offline storage.');
  const scope = scopeOf(session);
  await transaction(['meta', ...PRIVATE_STORES], async (s) => {
    const old = await requestValue(s.meta.get('context'));
    if (old && old.scope !== scope) for (const name of PRIVATE_STORES) s[name].clear();
    s.meta.put({
      key: 'context',
      scope,
      session: identity(session),
      expires_at: Date.now() + 8 * 3600000,
    });
    s.meta.delete('logout_required');
  });
  return scope;
}
export async function clearPrivate(pendingLogout = false) {
  await transaction(['meta', ...PRIVATE_STORES], (s) => {
    for (const name of PRIVATE_STORES) s[name].clear();
    s.meta.clear();
    s.meta.put({ key: 'logout_required', value: pendingLogout });
  });
}
async function requireScope(stores, scope) {
  const active = await requestValue(stores.meta.get('context'));
  if (!active || active.scope !== scope)
    throw new Error('Account or store changed. Reopen the correct workspace before saving.');
}
export async function list(store, scope) {
  return transaction(
    ['meta', store],
    async (s) => {
      await requireScope(s, scope);
      return requestValue(s[store].index('scope').getAll(scope));
    },
    'readonly',
  );
}
export async function getRecord(store, id, scope) {
  return (await list(store, scope)).find((row) => row.id === id);
}
export async function cacheCases(scope, cases) {
  const minimal = cases
    .filter((c) => c.status === 'review')
    .slice(0, 50)
    .map((c) => ({
      id: c.id,
      version: c.version,
      status: c.status,
      synthetic: c.synthetic,
      delivery_complete: c.delivery_complete,
      pricing_confirmed: c.pricing_confirmed,
      invoice: {
        supplier: c.invoice.supplier,
        reference: c.invoice.reference,
        date: c.invoice.date,
        lines: (c.invoice.lines || []).map((l) => ({
          name: l.name,
          billed: l.billed,
          unit: l.unit,
          price_paise: l.price_paise,
          received: l.received,
          received_unit: l.received_unit,
          unit_confirmed: l.unit_confirmed,
        })),
      },
    }));
  await transaction(['meta', 'cache'], async (s) => {
    await requireScope(s, scope);
    s.cache.put({
      id: scope,
      scope,
      cases: minimal,
      saved_at: Date.now(),
      expires_at: Date.now() + 86400000,
    });
  });
}
export async function saveDraft(scope, draft, file) {
  if (
    ![
      'invoice',
      'receiving',
      'purchase',
      'purchase_receiving',
      'inventory_movement',
      'business_entry',
    ].includes(draft.kind)
  )
    throw new Error('Unsupported device draft type.');
  let attachment;
  if (file) {
    if (!file.size || file.size > 4 * 1024 * 1024)
      throw new Error('Choose an image or PDF up to 4 MB for offline capture.');
    if (!['image/png', 'image/jpeg', 'image/webp', 'application/pdf'].includes(file.type))
      throw new Error('Use PNG, JPEG, WebP or PDF.');
    const digest = await crypto.subtle.digest('SHA-256', await file.arrayBuffer());
    attachment = {
      id: draft.id,
      scope,
      draft_id: draft.id,
      blob: file,
      name: file.name.slice(0, 120),
      mime: file.type,
      sha256: [...new Uint8Array(digest)].map((v) => v.toString(16).padStart(2, '0')).join(''),
      created_at: Date.now(),
    };
  }
  await transaction(['meta', 'drafts', 'attachments'], async (s) => {
    await requireScope(s, scope);
    const old = await requestValue(s.drafts.get(draft.id));
    if (old && old.state !== 'local_draft')
      throw new Error('Queued drafts are frozen. Resolve the operation before editing.');
    const attachments = await requestValue(s.attachments.index('scope').getAll(scope));
    if (
      attachment &&
      attachments.filter((a) => a.id !== draft.id).reduce((n, a) => n + a.blob.size, 0) +
        attachment.blob.size >
        40 * 1024 * 1024
    )
      throw new Error(
        'Offline attachment limit reached (40 MB). Sync or explicitly discard older drafts first.',
      );
    s.drafts.put({
      ...draft,
      scope,
      schema_version: 1,
      state: 'local_draft',
      updated_at: Date.now(),
      created_at: old?.created_at || Date.now(),
    });
    if (attachment) s.attachments.put(attachment);
  });
}
export function transition(row, state, patch = {}) {
  if (!moves[row.state]?.includes(state))
    throw new Error(`Invalid sync transition ${row.state} → ${state}`);
  return {
    ...row,
    ...patch,
    state,
    updated_at: Date.now(),
    transitions: [...(row.transitions || []), { state, at: Date.now() }].slice(-30),
  };
}
export async function queueDraft(scope, id) {
  return transaction(['meta', 'drafts', 'outbox', 'attachments'], async (s) => {
    await requireScope(s, scope);
    const draft = await requestValue(s.drafts.get(id));
    if (!draft || draft.scope !== scope || draft.schema_version !== 1)
      throw new Error('Draft schema needs attention. Keep it and update the app.');
    if (draft.state !== 'local_draft') throw new Error('This draft is already queued.');
    if (draft.kind === 'business_entry' && !draft.payload.merchant_confirmed)
      throw new Error('Review and confirm the manual record before queuing.');
    const opId = crypto.randomUUID();
    const row = {
      id: opId,
      operation_id: opId,
      scope,
      draft_id: id,
      operation_type: {
        business_entry: 'business_entry_create',
        invoice: 'invoice_create',
        receiving: 'receiving_save',
        purchase: 'purchase_create',
        purchase_receiving: 'purchase_receiving_capture',
        inventory_movement: 'inventory_movement',
      }[draft.kind],
      payload_schema_version: 1,
      entity_id: draft.entity_id || null,
      expected_version: draft.expected_version ?? null,
      client_created_at: new Date().toISOString(),
      dependency_ids: [],
      payload: draft.payload,
      state: 'local_draft',
      attempts: 0,
      next_attempt_at: 0,
    };
    const attachment = await requestValue(s.attachments.get(id));
    if (attachment && draft.kind === 'purchase')
      row.payload = {
        ...row.payload,
        document: { name: attachment.name, mime: attachment.mime, sha256: attachment.sha256 },
      };
    s.outbox.add(transition(row, 'pending_sync'));
    if (attachment && ['invoice', 'purchase'].includes(draft.kind)) {
      const attachmentId = crypto.randomUUID();
      s.outbox.add(
        transition(
          {
            ...row,
            id: attachmentId,
            operation_id: attachmentId,
            operation_type:
              draft.kind === 'purchase' ? 'purchase_document_upload' : 'attachment_upload',
            payload: null,
            attachment_id: id,
            entity_ref: opId,
            dependency_ids: [opId],
          },
          'pending_sync',
        ),
      );
    }
    s.drafts.put({ ...draft, state: 'pending_sync', operation_id: opId });
    return opId;
  });
}
export async function updateOperation(scope, id, state, patch = {}, leaseOwner = null) {
  return transaction(['meta', 'outbox', 'drafts', 'attachments', 'status'], async (s) => {
    await requireScope(s, scope);
    const old = await requestValue(s.outbox.get(id));
    if (!old || old.scope !== scope)
      throw new Error('Operation is not available in this workspace.');
    // A suspended tab may return after another tab has recovered its expired lease.
    // Only the current claimant may complete or fail that attempt.
    if (leaseOwner && (old.lease_owner !== leaseOwner || old.state !== 'syncing')) return old;
    const allowed = [
      'wire',
      'result',
      'error',
      'next_attempt_at',
      'lease_until',
      'attempts',
      'reviewed_at',
    ];
    if (Object.keys(patch).some((key) => !allowed.includes(key)))
      throw new Error(
        'Queued operation identity and payload are immutable. Create a revised draft instead.',
      );
    if (old.wire && patch.wire && JSON.stringify(old.wire) !== JSON.stringify(patch.wire))
      throw new Error('The exact queued request cannot change after an attempt.');
    if (patch.wire === null && state !== 'synced')
      throw new Error('Keep the frozen request until server acceptance is confirmed.');
    const row = state ? transition(old, state, patch) : { ...old, ...patch };
    s.outbox.put(row);
    const draft = await requestValue(s.drafts.get(row.draft_id));
    if (draft) {
      const related = (await requestValue(s.outbox.index('scope').getAll(scope)))
        .filter((o) => o.draft_id === draft.id)
        .map((o) => (o.id === id ? row : o));
      const done = related.every((o) => o.state === 'synced');
      s.drafts.put({
        ...draft,
        updated_at: Date.now(),
        ...(done ? { synced_at: Date.now() } : {}),
        state: done
          ? 'synced'
          : related.some((o) => o.state === 'conflict')
            ? 'conflict'
            : related.some((o) => o.state === 'needs_attention')
              ? 'needs_attention'
              : related.some((o) => o.state === 'syncing')
                ? 'syncing'
                : 'pending_sync',
        result: row.result || draft.result,
      });
      if (done) s.attachments.delete(draft.id);
    }
    if (state === 'synced') s.status.put({ id: scope, scope, last_synced_at: Date.now() });
    return row;
  });
}
export async function discardDraft(scope, id) {
  return transaction(['meta', 'drafts', 'attachments', 'outbox'], async (s) => {
    await requireScope(s, scope);
    const rows = (await requestValue(s.outbox.index('scope').getAll(scope))).filter(
      (o) => o.draft_id === id,
    );
    if (rows.some((o) => ['pending_sync', 'syncing'].includes(o.state)))
      throw new Error(
        'Wait for sync to stop before discarding. A request may have reached the server.',
      );
    s.drafts.delete(id);
    s.attachments.delete(id);
    rows.forEach((o) => s.outbox.delete(o.id));
  });
}
export async function cleanup(scope) {
  return transaction(['meta', 'cache', 'drafts', 'attachments', 'outbox'], async (s) => {
    await requireScope(s, scope);
    const cache = await requestValue(s.cache.get(scope));
    if (cache?.expires_at < Date.now()) s.cache.delete(scope);
    for (const draft of await requestValue(s.drafts.index('scope').getAll(scope))) {
      if (
        draft.state === 'synced' &&
        (draft.synced_at || draft.updated_at) < Date.now() - 7 * 86400000
      ) {
        s.drafts.delete(draft.id);
        s.attachments.delete(draft.id);
        for (const op of await requestValue(s.outbox.index('scope').getAll(scope)))
          if (op.draft_id === draft.id) s.outbox.delete(op.id);
      }
    }
  });
}
export async function claimOperation(scope, id, owner, now = Date.now()) {
  return transaction(['meta', 'outbox', 'drafts'], async (s) => {
    await requireScope(s, scope);
    let row = await requestValue(s.outbox.get(id));
    if (!row || row.scope !== scope) return null;
    if (row.state === 'syncing' && row.lease_until <= now) row = transition(row, 'pending_sync');
    if (row.state !== 'pending_sync' || row.next_attempt_at > now) return null;
    row = transition(row, 'syncing', {
      lease_owner: owner,
      lease_until: now + 45000,
      attempts: row.attempts + 1,
    });
    s.outbox.put(row);
    const draft = await requestValue(s.drafts.get(row.draft_id));
    if (draft) s.drafts.put({ ...draft, state: 'syncing' });
    return row;
  });
}
