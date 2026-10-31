import React, { useState, useEffect } from 'react';
import { useSession } from '../session';
import { api, money, today, saveBlob } from '../api';
import { Commerce, CommerceDraftFields } from '../components/Commerce';
import { RecordDraftFields } from '../components/RecordDraftFields';
import { InvoiceFields } from '../components/InvoiceIntake';
import { ErrorBox, Busy } from '../components/ui';
import { useOffline } from './provider';
import * as db from './db';
export const stateLabel = (state) =>
  ({
    local_draft: 'Saved on this device',
    pending_sync: 'Waiting to sync',
    syncing: 'Syncing',
    synced: 'Synced',
    needs_attention: 'Needs attention',
    conflict: 'Conflict',
  })[state] || 'Needs attention';
const fresh = () => ({
  id: crypto.randomUUID(),
  kind: 'invoice',
  payload: {
    invoice: {
      supplier: '',
      supplier_phone: '',
      reference: '',
      date: today(),
      pricing_note: 'Verify effective prices after taxes, discounts and schemes.',
      lines: [
        {
          name: '',
          billed: 1,
          unit: 'pack',
          price_paise: 0,
          received: null,
          received_unit: 'unknown',
          unit_confirmed: false,
          note: '',
        },
      ],
    },
  },
});
const receiving = (c) => ({
  id: crypto.randomUUID(),
  kind: 'receiving',
  entity_id: c.id,
  expected_version: c.version,
  source: c,
  payload: {
    lines: c.invoice.lines.map((l) => ({
      received: l.received,
      received_unit: l.received_unit,
      unit_confirmed: l.unit_confirmed,
    })),
    delivery_complete: c.delivery_complete,
    pricing_confirmed: c.pricing_confirmed,
    note: '',
  },
});
const when = (t) => (t ? new Date(t).toLocaleString('en-IN') : 'Not yet');
export function OfflineWorkspace({ standalone = false, onClose, onServerChange }) {
  const session = useSession(),
    local = useOffline();
  const [commerce, setCommerce] = useState(false);
  const [editor, setEditor] = useState(null),
    [file, setFile] = useState(null),
    [error, setError] = useState(''),
    [busy, setBusy] = useState(false),
    [notice, setNotice] = useState(''),
    [conflict, setConflict] = useState(null);
  const [preview, setPreview] = useState('');
  useEffect(() => {
    if (!file) {
      setPreview('');
      return;
    }
    const url = URL.createObjectURL(file);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);
  const changePayload = (payload) => setEditor({ ...editor, payload });
  async function act(fn) {
    setBusy(true);
    setError('');
    try {
      await fn();
      await local.refresh();
    } catch (e) {
      setError(db.storageMessage(e));
    } finally {
      setBusy(false);
    }
  }
  async function reviewConflict(draft) {
    setError('');
    try {
      if (!local.online)
        throw new Error(
          'Reconnect to inspect the latest server record. Your local version remains saved.',
        );
      if (draft.kind === 'receiving') {
        const latest = await api(`/cases/${draft.entity_id}`);
        setConflict({ draft, latest });
      } else {
        let copy = { ...draft, id: crypto.randomUUID(), state: 'local_draft' };
        if (draft.kind === 'business_entry')
          copy.payload = { ...draft.payload, merchant_confirmed: false };
        if (draft.kind === 'purchase_receiving') {
          const latest = await api(`/purchases/${draft.entity_id}`);
          if (latest.status !== 'accepted' || latest.delivery_complete)
            throw new Error(
              'This purchase is no longer open for receiving. Keep the original draft and inspect its accepted receipts.',
            );
          copy = {
            ...copy,
            expected_version: latest.version,
            payload: { ...draft.payload, purchase_version: latest.version },
          };
        } else if (draft.kind === 'inventory_movement') {
          const latest = (await api('/products')).find((p) => p.id === draft.entity_id);
          if (!latest) throw new Error('This item is no longer available in your shop.');
          copy = {
            ...copy,
            expected_version: latest.stock_version,
            payload: {
              ...draft.payload,
              movement: { ...draft.payload.movement, expected_stock_version: latest.stock_version },
            },
          };
        }
        setEditor(copy);
        const attachment = await db.getRecord('attachments', draft.id, local.scope);
        setFile(
          attachment?.blob
            ? new File([attachment.blob], attachment.name, { type: attachment.mime })
            : null,
        );
        setNotice(
          'An editable copy is ready. Check quantities, stock and bill details before syncing. Your earlier record is kept.',
        );
      }
    } catch (e) {
      setError(e.message);
    }
  }
  async function discard(draft) {
    if (
      window.confirm(
        'Discard this device copy and its attachments? Accepted server records will remain.',
      )
    )
      await act(() => db.discardDraft(local.scope, draft.id));
  }
  const queued = local.operations.filter((o) => o.state !== 'synced');
  return (
    <section className="offline-workspace panel" aria-label="Offline workspace">
      <div className="panel-heading">
        <div>
          <div className="eyebrow">PRIVATE DEVICE WORKSPACE</div>
          <h1>Drafts & sync</h1>
          <p>
            {local.online && !session.offlineAccess
              ? 'Connected · server acceptance is required'
              : 'Offline drafts · no server acceptance'}
          </p>
        </div>
        {onClose && (
          <button className="button secondary" onClick={onClose}>
            Back to business
          </button>
        )}
      </div>
      {session.store.demo && <p className="demo-note">Demo store · Sample records only.</p>}
      <p>
        Last server sync: <strong>{when(local.status?.last_synced_at)}</strong>. Cached receiving
        list: {when(local.cache?.saved_at)} (expires after 24 hours).
      </p>
      <p className="info-box">
        Entries saved on this phone still need checking. No stock, money or supplier message is
        confirmed or sent here. Cloud OCR, translation, Paytm queries and AI require connectivity;
        enter the bill manually below.
      </p>
      <ErrorBox text={error || local.error || session.offlineUnavailable} />
      {notice && (
        <p role="status" className="info-box">
          {notice}
        </p>
      )}
      <div className="offline-actions">
        <button
          className="button primary"
          disabled={busy || !session.permissions.includes('write')}
          onClick={() => {
            setEditor(fresh());
            setFile(null);
            setError('');
            setNotice('');
          }}
        >
          New offline invoice
        </button>
        <button
          className="button secondary"
          disabled={busy || local.busy || !local.online || session.offlineAccess}
          onClick={() =>
            act(async () => {
              await local.sync();
              onServerChange?.();
            })
          }
        >
          {local.busy ? 'Syncing…' : 'Sync now'}
        </button>
        <button
          className="button secondary"
          onClick={() =>
            act(async () => {
              const granted = await navigator.storage?.persist?.();
              setNotice(
                granted
                  ? 'Browser granted persistent storage. This is not encryption or a backup.'
                  : 'Persistent storage was not granted or is unsupported. Keep a backup of important unsynced drafts.',
              );
            })
          }
        >
          Protect device storage
        </button>
      </div>
      <label className="field">
        Receiving draft from cached unapproved invoice
        <select
          aria-label="Choose invoice for offline receiving"
          value=""
          disabled={!session.permissions.includes('write')}
          onChange={(e) => {
            const c = local.cache?.cases.find((c) => c.id === e.target.value);
            if (c) {
              setEditor(receiving(c));
              setFile(null);
              setNotice('');
            }
          }}
        >
          <option value="">Choose an invoice</option>
          {local.cache?.cases
            .filter((c) => c.status === 'review')
            .map((c) => (
              <option key={c.id} value={c.id}>
                {c.invoice.reference} · {c.invoice.supplier}
              </option>
            ))}
        </select>
      </label>
      {!local.cache && (
        <p>
          No fresh receiving cache. Connect and load Purchases first. You can still create a manual
          invoice.
        </p>
      )}
      <button className="button secondary" onClick={() => setCommerce(!commerce)}>
        Purchase and stock draft editors
      </button>
      {commerce && (
        <Commerce
          openCase={() => setNotice('Connect and open the linked recovery case from Purchases.')}
        />
      )}
      {editor && (
        <form
          className="offline-editor"
          onSubmit={(e) => {
            e.preventDefault();
            act(async () => {
              await db.saveDraft(local.scope, editor, file);
              setEditor(null);
              setFile(null);
              setNotice('Saved on this device. Queue it explicitly when ready.');
            });
          }}
        >
          <h2>
            {editor.kind === 'invoice'
              ? 'Manual invoice draft'
              : `${editor.kind} · ${editor.source?.invoice?.reference || editor.payload?.reference || editor.payload?.draft?.reference || editor.entity_id || 'New draft'}`}
          </h2>
          {editor.kind === 'business_entry' ? (
            <RecordDraftFields payload={editor.payload} change={changePayload} />
          ) : !['invoice', 'receiving'].includes(editor.kind) ? (
            <CommerceDraftFields
              kind={editor.kind}
              payload={editor.payload}
              change={changePayload}
            />
          ) : editor.kind === 'invoice' ? (
            <InvoiceFields
              draft
              review
              invoice={editor.payload.invoice}
              change={(invoice) => changePayload({ invoice })}
            />
          ) : (
            <>
              <p>Saved as a receiving draft; approval stays online.</p>
              {editor.source.invoice.lines.map((line, i) => (
                <div className="line-editor" key={i}>
                  <h3>{line.name}</h3>
                  <p>
                    {line.billed} {line.unit} billed · {money(line.price_paise)} per unit
                  </p>
                  <label className="field">
                    Actually received
                    <input
                      type="number"
                      min="0"
                      max="100000"
                      step="0.000001"
                      value={editor.payload.lines[i].received ?? ''}
                      onChange={(e) =>
                        changePayload({
                          ...editor.payload,
                          lines: editor.payload.lines.map((l, n) =>
                            n === i ? { ...l, received: e.target.value || null } : l,
                          ),
                        })
                      }
                    />
                  </label>
                  <label className="field">
                    Received unit
                    <select
                      value={editor.payload.lines[i].received_unit}
                      onChange={(e) =>
                        changePayload({
                          ...editor.payload,
                          lines: editor.payload.lines.map((l, n) =>
                            n === i
                              ? { ...l, received_unit: e.target.value, unit_confirmed: false }
                              : l,
                          ),
                        })
                      }
                    >
                      {['unknown', 'pack', 'piece', 'carton', 'kg'].map((u) => (
                        <option key={u}>{u}</option>
                      ))}
                    </select>
                  </label>
                  <label className="check-field">
                    <input
                      type="checkbox"
                      checked={editor.payload.lines[i].unit_confirmed}
                      onChange={(e) =>
                        changePayload({
                          ...editor.payload,
                          lines: editor.payload.lines.map((l, n) =>
                            n === i ? { ...l, unit_confirmed: e.target.checked } : l,
                          ),
                        })
                      }
                    />
                    I checked that billed and received units match.
                  </label>
                </div>
              ))}
              <label className="check-field">
                <input
                  type="checkbox"
                  checked={editor.payload.delivery_complete}
                  onChange={(e) =>
                    changePayload({ ...editor.payload, delivery_complete: e.target.checked })
                  }
                />
                The delivery is complete.
              </label>
              <label className="check-field">
                <input
                  type="checkbox"
                  checked={editor.payload.pricing_confirmed}
                  onChange={(e) =>
                    changePayload({ ...editor.payload, pricing_confirmed: e.target.checked })
                  }
                />
                I verified effective unit prices.
              </label>
            </>
          )}
          {['invoice', 'receiving'].includes(editor.kind) && (
            <label className="field">
              Invoice / receiving notes
              <textarea
                maxLength={500}
                value={
                  editor.kind === 'invoice'
                    ? editor.payload.invoice.pricing_note
                    : editor.payload.note || ''
                }
                onChange={(e) =>
                  editor.kind === 'invoice'
                    ? changePayload({
                        invoice: { ...editor.payload.invoice, pricing_note: e.target.value },
                      })
                    : changePayload({ ...editor.payload, note: e.target.value })
                }
              />
            </label>
          )}
          {['invoice', 'purchase'].includes(editor.kind) && (
            <label className="field">
              Capture invoice attachment (optional, up to 4 MB)
              <input
                type="file"
                accept="image/png,image/jpeg,image/webp,application/pdf"
                onChange={(e) => {
                  setFile(e.target.files[0] || null);
                  setNotice('File selected; save the draft to store it on this device.');
                }}
              />
            </label>
          )}
          {file && (
            <p>
              {file.name} · {file.size} bytes · not uploaded
            </p>
          )}
          {preview && file?.type.startsWith('image/') && (
            <img
              className="local-preview"
              src={preview}
              alt="Selected invoice attachment preview"
            />
          )}
          {preview && file?.type === 'application/pdf' && (
            <a href={preview} target="_blank" rel="noreferrer">
              Preview local PDF
            </a>
          )}
          <p>
            Preview:{' '}
            {editor.kind === 'invoice'
              ? editor.payload.invoice.reference
              : editor.source?.invoice?.reference ||
                editor.payload?.draft?.reference ||
                editor.entity_id}{' '}
            ·{' '}
            {editor.kind === 'invoice'
              ? editor.payload.invoice.lines.length
              : (editor.payload.draft?.lines || editor.payload.lines || []).length}{' '}
            items. Amounts and eligibility will be checked on the server.
          </p>
          <div className="offline-actions">
            <button className="button primary" disabled={busy}>
              <Busy busy={busy}>Save on this device</Busy>
            </button>
            <button
              type="button"
              className="button secondary"
              onClick={() =>
                act(() =>
                  saveBlob(
                    new Blob([JSON.stringify(editor, null, 2)], { type: 'application/json' }),
                    'munafa-local-draft.json',
                  ),
                )
              }
            >
              Back up open draft
            </button>
            <button
              type="button"
              className="button secondary"
              onClick={() => {
                if (
                  window.confirm(
                    'Close this form? Changes since the last device save will be lost.',
                  )
                ) {
                  setEditor(null);
                  setFile(null);
                }
              }}
            >
              Close draft editor
            </button>
          </div>
        </form>
      )}
      {conflict && (
        <section className="conflict-review" role="region" aria-label="Resolve receiving conflict">
          <h2>Review receiving conflict</h2>
          <p>
            This record changed while you were offline. Compare it with your saved draft:{' '}
            {conflict.latest.status}. Nothing has been overwritten.
          </p>
          <p>
            Local counts:{' '}
            {conflict.draft.payload.lines
              .map((l) => `${l.received ?? '?'} ${l.received_unit}`)
              .join(' · ')}
          </p>
          <p>
            Latest saved counts:{' '}
            {conflict.latest.invoice.lines
              .map((l) => `${l.name}: ${l.received ?? '?'} ${l.received_unit}`)
              .join(' · ')}
          </p>
          <button
            className="button secondary"
            disabled={conflict.latest.status !== 'review'}
            onClick={() => {
              setEditor(receiving(conflict.latest));
              setConflict(null);
              setNotice(
                'Review the latest record and enter your counts again. Nothing changes until you save and sync.',
              );
            }}
          >
            Create revised receiving draft
          </button>
          <button className="button secondary" onClick={() => setConflict(null)}>
            Keep conflict for later
          </button>
        </section>
      )}
      <h2>Device drafts</h2>
      {!local.ready && <p role="status">Loading device drafts…</p>}
      {local.ready && local.drafts.length === 0 && (
        <p>No saved device drafts. Create a manual invoice even without a connection.</p>
      )}
      {local.drafts.map((d) => (
        <article key={d.id} className="offline-list-card">
          <strong>
            {d.kind === 'invoice'
              ? d.payload?.invoice?.reference || 'Untitled invoice'
              : `${d.kind}: ${d.payload?.reference || d.payload?.draft?.reference || d.source?.invoice?.reference || d.entity_id || 'New draft'}`}
          </strong>
          <span className={`sync-state ${d.state}`}>{stateLabel(d.state)}</span>
          <p>
            Saved {when(d.updated_at)}
            {d.updated_at < Date.now() - 30 * 86400000
              ? ' · Older than 30 days: review before syncing.'
              : ''}
          </p>
          {d.state === 'synced' && (
            <p>Server case {d.result?.entity_id}; retained here for seven days.</p>
          )}
          {d.state === 'local_draft' &&
            d.schema_version === 1 &&
            [
              'invoice',
              'receiving',
              'purchase',
              'purchase_receiving',
              'inventory_movement',
              'business_entry',
            ].includes(d.kind) && (
              <>
                <button
                  className="button secondary"
                  onClick={async () => {
                    setEditor(d);
                    try {
                      const a = await db.getRecord('attachments', d.id, local.scope);
                      setFile(a?.blob ? new File([a.blob], a.name, { type: a.mime }) : null);
                    } catch (e) {
                      setError(db.storageMessage(e));
                    }
                    setNotice(
                      'Previously saved attachments remain with this draft unless replaced.',
                    );
                  }}
                >
                  Edit draft
                </button>
                <button
                  className="button primary"
                  disabled={busy}
                  onClick={() =>
                    act(async () => {
                      await db.queueDraft(local.scope, d.id);
                      setNotice('Waiting to sync. Server records have not changed yet.');
                      await local.sync();
                    })
                  }
                >
                  Queue for sync
                </button>
              </>
            )}
          {['conflict', 'needs_attention'].includes(d.state) && (
            <button className="button secondary" onClick={() => reviewConflict(d)}>
              Review / revise draft
            </button>
          )}
          <button
            className="button secondary"
            onClick={() =>
              act(() =>
                saveBlob(
                  new Blob([JSON.stringify(d, null, 2)], { type: 'application/json' }),
                  'munafa-device-draft.json',
                ),
              )
            }
          >
            Back up device draft
          </button>
          {!['pending_sync', 'syncing'].includes(d.state) && (
            <button className="button secondary" onClick={() => discard(d)}>
              Discard device copy
            </button>
          )}
        </article>
      ))}
      <h2>Sync activity · {queued.length} unfinished</h2>
      {local.operations.map((o) => (
        <article className="offline-list-card" key={o.id}>
          <strong>{o.operation_type.replaceAll('_', ' ')}</strong>
          <span className={`sync-state ${o.state}`}>{stateLabel(o.state)}</span>
          <p>
            {o.error ||
              (o.state === 'synced'
                ? 'Synced and saved.'
                : 'Waiting to sync. Your saved records have not changed yet.')}
          </p>
          {o.state === 'needs_attention' && (
            <button
              className="button secondary"
              disabled={busy || !local.online || session.offlineAccess}
              onClick={() =>
                act(async () => {
                  await db.updateOperation(local.scope, o.id, 'pending_sync', {
                    attempts: 0,
                    next_attempt_at: 0,
                    reviewed_at: Date.now(),
                    error: '',
                  });
                  await local.sync();
                })
              }
            >
              Retry sync
            </button>
          )}
        </article>
      ))}
      {import.meta.env.DEV && new URLSearchParams(window.location.search).get('debug') === '1' && (
        <details className="sync-debug">
          <summary>Sync diagnostics (development only)</summary>
          <p>
            Waiting to send: {local.operations.length}. Failed:{' '}
            {
              local.operations.filter((o) => ['conflict', 'needs_attention'].includes(o.state))
                .length
            }
            .
          </p>
          {local.operations.map((o) => (
            <p key={o.id}>
              {o.id} · {o.state} · attempts {o.attempts}
            </p>
          ))}
        </details>
      )}
      <p className="muted">
        Browser storage is not encrypted by this app. Shared-device users and same-origin scripts
        may read it. Browsers may evict it; unsynced drafts cannot be reconstructed from the server.
        Active drafts are retained until you discard or sign out; synced copies expire after seven
        days.
      </p>
      {session.offlineAccess && (
        <button className="button secondary" disabled={!local.online} onClick={session.reconnect}>
          Reconnect to server
        </button>
      )}
      {standalone && (
        <button className="button secondary" onClick={session.logout}>
          Sign out and clear device
        </button>
      )}
    </section>
  );
}
