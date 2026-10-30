import {
  activate,
  context,
  scopeOf,
  list,
  getRecord,
  claimOperation,
  updateOperation,
} from './db.js';
export const MAX_ATTEMPTS = 5;
export const BATCH_SIZE = 3;
export const retryDelay = (attempt, random = Math.random) =>
  Math.min(60000, 1000 * 2 ** Math.max(0, attempt - 1)) * (0.75 + random() * 0.5);
function base64(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result.split(',')[1]);
    reader.onerror = () =>
      reject(
        new Error('Attachment cannot be read. Keep the draft and select the original file again.'),
      );
    reader.readAsDataURL(blob);
  });
}
export async function makeWire(row, rows, scope) {
  if (row.wire) return row.wire;
  let entity = row.entity_id,
    version = row.expected_version,
    payload = row.payload;
  if (row.entity_ref) {
    const parent = rows.find((o) => o.id === row.entity_ref);
    if (parent?.state !== 'synced') throw new Error('Waiting for the invoice to reach the server.');
    entity = parent.result.entity_id;
    version = parent.result.entity_version;
  }
  if (
    ['attachment_upload', 'purchase_document_upload', 'proof_upload'].includes(row.operation_type)
  ) {
    const a = await getRecord('attachments', row.attachment_id, scope);
    if (!a?.blob)
      throw new Error(
        'Attachment is missing from device storage. Keep the draft and inspect the server before replacing it.',
      );
    payload = {
      name: a.name,
      mime: a.mime,
      sha256: a.sha256,
      content_base64: await base64(a.blob),
    };
  }
  return {
    operation_id: row.operation_id,
    operation_type: row.operation_type,
    payload_schema_version: row.payload_schema_version,
    entity_id: entity,
    expected_version: version,
    client_created_at: row.client_created_at,
    dependency_ids: row.dependency_ids,
    payload,
  };
}
export function failureState(error, attempts) {
  if (error.status === 409) return 'conflict';
  if (
    [400, 403, 404, 413, 422].includes(error.status) ||
    error.status === 401 ||
    attempts >= MAX_ATTEMPTS
  )
    return 'needs_attention';
  return 'pending_sync';
}
export async function syncBatch({
  scope,
  api,
  signal,
  online = () => navigator.onLine,
  owner = crypto.randomUUID(),
}) {
  if (!online() || signal?.aborted) return;
  // A cached identity is not authentication. Verify membership before every bounded batch.
  const verified = await api('/auth/me', { signal });
  if (scopeOf(verified) !== scope || (await context())?.scope !== scope) {
    const error = new Error(
      'Account or membership changed. Device data must be cleared before syncing.',
    );
    error.status = 403;
    throw error;
  }
  await activate(verified);
  let count = 0;
  const rows = await list('outbox', scope);
  for (const candidate of rows.sort((a, b) =>
    String(a.client_created_at || '').localeCompare(String(b.client_created_at || '')),
  )) {
    if (count >= BATCH_SIZE || signal?.aborted || !online()) break;
    if (candidate.payload_schema_version !== 1) {
      if (candidate.state === 'pending_sync')
        await updateOperation(scope, candidate.id, 'needs_attention', {
          error: 'Saved operation schema is unsupported. Update the app; do not discard it.',
        });
      continue;
    }
    if (!['pending_sync', 'syncing'].includes(candidate.state)) continue;
    if (candidate.state === 'syncing' && candidate.lease_until > Date.now()) continue;
    if (
      !Array.isArray(candidate.dependency_ids) ||
      !Number.isFinite(Date.parse(candidate.client_created_at))
    ) {
      await updateOperation(scope, candidate.id, 'needs_attention', {
        error:
          'Saved operation metadata is corrupted. Keep the device draft and inspect the server before revising.',
      });
      continue;
    }
    if (
      candidate.attempts >= MAX_ATTEMPTS ||
      Math.max(new Date(candidate.client_created_at).getTime(), candidate.reviewed_at || 0) <
        Date.now() - 30 * 86400000
    ) {
      await updateOperation(scope, candidate.id, 'needs_attention', {
        error: 'Automatic retries stopped. Review this saved operation before retrying unchanged.',
      });
      continue;
    }
    const missing = candidate.dependency_ids.some((id) => !rows.some((o) => o.id === id));
    if (missing && candidate.state === 'pending_sync') {
      await updateOperation(scope, candidate.id, 'needs_attention', {
        error:
          'A prerequisite is missing from device storage. Inspect the server before revising this draft.',
      });
      continue;
    }

    if (candidate.dependency_ids.some((id) => rows.find((o) => o.id === id)?.state !== 'synced')) {
      const blocked = candidate.dependency_ids.some((id) =>
        ['conflict', 'needs_attention'].includes(rows.find((o) => o.id === id)?.state),
      );
      if (blocked && candidate.state === 'pending_sync')
        await updateOperation(scope, candidate.id, 'needs_attention', {
          error: 'A prerequisite needs attention. Resolve the invoice first.',
        });
      continue;
    }
    const row = await claimOperation(scope, candidate.id, owner);
    if (!row) continue;
    count++;
    try {
      const wire = await makeWire(row, rows, scope);
      const frozen = await updateOperation(scope, row.id, null, { wire }, owner);
      if (
        frozen.lease_owner !== owner ||
        frozen.state !== 'syncing' ||
        frozen.lease_until <= Date.now()
      )
        continue;
      if (signal?.aborted || (await context())?.scope !== scope) break;
      const result = await api('/sync/operations', {
        method: 'POST',
        body: wire,
        signal,
        timeout: 12000,
        headers: { 'Idempotency-Key': row.operation_id },
      });
      if (
        result.operation_id !== row.operation_id ||
        !result.entity_id ||
        !Number.isInteger(result.entity_version)
      )
        throw new Error('The sync receipt is incomplete. Retry with the same operation ID.');
      if ((await context())?.scope !== scope) break;
      const saved = await updateOperation(
        scope,
        row.id,
        'synced',
        {
          result,
          error: '',
          wire: null,
          lease_until: 0,
        },
        owner,
      );
      Object.assign(
        rows.find((o) => o.id === row.id),
        saved,
      );
    } catch (error) {
      if ((await context())?.scope !== scope) break;
      const state = failureState(error, row.attempts);
      await updateOperation(
        scope,
        row.id,
        state,
        {
          error:
            error.status === 401
              ? 'Session expired. Sign in as the same merchant, then retry.'
              : error.message,
          next_attempt_at: Date.now() + retryDelay(row.attempts),
          lease_until: 0,
          // An expired session pauses without consuming the network retry budget.
          ...(error.status === 401 ? { attempts: Math.max(0, row.attempts - 1) } : {}),
        },
        owner,
      );
      if (error.status === 401 || error.status === 403) throw error;
    }
  }
  return count;
}
