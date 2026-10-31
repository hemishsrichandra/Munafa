import React, { useState, useEffect, useRef } from 'react';
import { useLanguage } from '../language';
import { Modal } from './ui';
import { ExpiryRadar } from './ExpiryRadar';
import { hasMissingItems } from '../merchant-display.mjs';
import { Plus, FileText, Package, CalendarClock, ChevronRight } from 'lucide-react';
import { api, money, today, downloadPrivate, proposeCommerceAction } from '../api';
import { MoneyInput } from './MoneyInput';
import { useOffline } from '../offline/provider';
import * as db from '../offline/db';
const units = ['pack', 'piece', 'carton', 'kg'];
const line = () => ({
  description: '',
  product_id: null,
  billed_quantity: '',
  unit: 'pack',
  unit_price_paise: null,
  effective_price_paise: null,
});
const fresh = () => ({
  supplier: '',
  reference: '',
  date: today(),
  lines: [line()],
  tax_paise: 0,
  discount_paise: 0,
  total_paise: null,
});
export function CommerceDraftFields({ kind, payload, change }) {
  const d =
    kind === 'purchase'
      ? payload.draft
      : kind === 'inventory_movement'
        ? payload.movement
        : payload;
  const set = (next) =>
    change(
      kind === 'purchase'
        ? { ...payload, draft: next }
        : kind === 'inventory_movement'
          ? { ...payload, movement: next, merchant_confirmed: true }
          : next,
    );
  const fields =
    kind === 'purchase'
      ? [
          'supplier',
          'reference',
          'date',
          'subtotal_paise',
          'tax_paise',
          'discount_paise',
          'rounding_paise',
          'total_paise',
        ]
      : kind === 'inventory_movement'
        ? ['quantity', 'reference', 'reason', 'occurred_on']
        : ['received_on', 'note'];
  return (
    <>
      <p>Saved on this device. Review the details before adding them to your records.</p>
      <div className="form-grid">
        {fields.map((k) => {
          const Component = k.endsWith('_paise') ? MoneyInput : Input;
          return (
            <Component
              key={k}
              label={
                k.endsWith('_paise')
                  ? k.replace('_paise', '').replaceAll('_', ' ') + ' (₹)'
                  : k.replaceAll('_', ' ')
              }
              signed={k === 'rounding_paise'}
              value={d[k]}
              change={(v) => set({ ...d, [k]: v })}
            />
          );
        })}
      </div>
      {d.lines?.map((l, i) => {
        const update = (k, v) =>
          set({
            ...d,
            lines: d.lines.map((x, j) =>
              j === i ? { ...x, [k]: v, ...(k === 'unit' ? { unit_confirmed: false } : {}) } : x,
            ),
          });
        return (
          <div className="panel" key={i}>
            <h3>Item {i + 1}</h3>
            {(kind === 'purchase'
              ? ['description', 'billed_quantity', 'unit_price_paise', 'effective_price_paise']
              : ['quantity', 'damaged_quantity', 'batch_reference', 'expiry_date']
            ).map((k) => {
              const Component = k.endsWith('_paise') ? MoneyInput : Input;
              return (
                <Component
                  key={k}
                  label={
                    k.endsWith('_paise')
                      ? k.replace('_paise', '').replaceAll('_', ' ') + ' (₹)'
                      : k.replaceAll('_', ' ')
                  }
                  value={l[k]}
                  change={(v) => update(k, k.endsWith('_paise') ? v : v || null)}
                />
              );
            })}
            <Unit
              value={l.unit}
              change={(v) => {
                update('unit', v);
              }}
            />
            {kind !== 'purchase' && (
              <label>
                <input
                  type="checkbox"
                  checked={l.unit_confirmed}
                  onChange={(e) => update('unit_confirmed', e.target.checked)}
                />
                Units checked
              </label>
            )}
          </div>
        );
      })}
      {kind === 'purchase_receiving' &&
        ['delivery_complete', 'pricing_confirmed'].map((k) => (
          <label className="check-field" key={k}>
            <input
              type="checkbox"
              checked={d[k]}
              onChange={(e) => set({ ...d, [k]: e.target.checked })}
            />
            {k.replaceAll('_', ' ')}
          </label>
        ))}
    </>
  );
}
function Field({ label, children }) {
  const { t } = useLanguage();
  return (
    <label className="field">
      {t(label)}
      {children}
    </label>
  );
}
function DocumentPreview({ document }) {
  const [url, setUrl] = useState(''),
    [error, setError] = useState('');
  useEffect(
    () => () => {
      if (url) URL.revokeObjectURL(url);
    },
    [url],
  );
  return (
    <div>
      <button
        className="text-button"
        onClick={async () => {
          try {
            setError('');
            setUrl(
              URL.createObjectURL(
                await downloadPrivate(
                  `/api/purchase-documents/${document.id}`,
                  document.name,
                  true,
                ),
              ),
            );
          } catch (e) {
            setError(e.message);
          }
        }}
      >
        Preview {document.name}
      </button>
      {error && <p role="alert">{error}</p>}
      {url &&
        (document.mime.startsWith('image/') ? (
          <img className="local-preview" src={url} alt="Original purchase bill" />
        ) : (
          <a href={url} target="_blank" rel="noreferrer">
            Open original PDF or text
          </a>
        ))}
    </div>
  );
}
function Input({ label, value, change, type = 'text' }) {
  return (
    <Field label={label}>
      <input type={type} value={value ?? ''} onChange={(e) => change(e.target.value)} />
    </Field>
  );
}
function Unit({ value, change }) {
  return (
    <Field label="Unit">
      <select value={value || ''} onChange={(e) => change(e.target.value)}>
        <option value="">Confirm unit</option>
        {units.map((u) => (
          <option key={u}>{u}</option>
        ))}
      </select>
    </Field>
  );
}
function ConversionForm({ product, onSave }) {
  const [from, setFrom] = useState('pack'),
    [factor, setFactor] = useState(''),
    [reason, setReason] = useState(''),
    [error, setError] = useState(''),
    [busy, setBusy] = useState(false);
  return (
    <form
      onSubmit={async (e) => {
        e.preventDefault();
        setBusy(true);
        setError('');
        try {
          await api(`/products/${product.id}/conversions`, {
            method: 'POST',
            body: { from_unit: from, to_unit: product.unit, factor, provenance: reason },
          });
          setFactor('');
          setReason('');
          onSave();
        } catch (e) {
          setError(e.message);
        } finally {
          setBusy(false);
        }
      }}
    >
      <h4>Define a checked conversion to {product.unit}</h4>
      <p>Example: 1 carton contains 24 pieces. Confirm the package, not an assumed conversion.</p>
      <Unit value={from} change={setFrom} />
      <Input label={`Number of ${product.unit} in one ${from}`} value={factor} change={setFactor} />
      <Input label="Conversion evidence / source" value={reason} change={setReason} />
      {error && <p role="alert">{error}</p>}
      <button className="button secondary" disabled={busy || !navigator.onLine}>
        Confirm conversion
      </button>
    </form>
  );
}
export function Commerce({ openCase, initialRoute = '' }) {
  const { t } = useLanguage();
  const [leaveIntent, setLeaveIntent] = useState(null);
  const [openingCase, setOpeningCase] = useState(false);
  const uploadAttempt = useRef(null);
  const [deviceSaved, setDeviceSaved] = useState(null);
  const editorTop = useRef(null);
  const local = useOffline();
  const [tab, setTab] = useState('purchases'),
    [purchases, setPurchases] = useState([]),
    [products, setProducts] = useState([]),
    [expiry, setExpiry] = useState([]),
    [expiryAsOf, setExpiryAsOf] = useState(null),
    [expiryStale, setExpiryStale] = useState(false),
    [expiryLoaded, setExpiryLoaded] = useState(false),
    [reorders, setReorders] = useState([]),
    [selected, setSelected] = useState(null),
    [draft, setDraft] = useState(null),
    [receiving, setReceiving] = useState(null),
    [editReceipt, setEditReceipt] = useState(null),
    [file, setFile] = useState(null),
    [text, setText] = useState(''),
    [error, setError] = useState(''),
    [notice, setNotice] = useState(''),
    [busy, setBusy] = useState(false),
    [movements, setMovements] = useState(null),
    [sku, setSku] = useState(null),
    [movement, setMovement] = useState(null),
    [draftId, setDraftId] = useState(() => crypto.randomUUID());
  async function load() {
    if (!navigator.onLine) {
      const cached = await db.getRecord('cache', `${local.scope}:commerce`, local.scope);
      if (cached && cached.expires_at > Date.now()) {
        setPurchases(cached.purchases);
        setProducts(cached.products);
        setExpiry(cached.expiry);
        setExpiryAsOf(cached.expiry_as_of || null);
        setExpiryStale(true);
        setExpiryLoaded(true);
        setNotice('Saved on your phone: stock may have changed. Reconnect before confirming.');
      }
      return;
    }
    const [ps, sk, ex, reorderData] = await Promise.all([
      api('/purchases'),
      api('/products'),
      api('/inventory/expiry'),
      api('/inventory/reorder-suggestions').catch(() => ({ suggestions: [] })),
    ]);
    setPurchases(ps);
    setProducts(sk);
    setExpiry(ex.lots);
    setExpiryAsOf(ex.as_of);
    setExpiryStale(false);
    setExpiryLoaded(true);
    setReorders(reorderData.suggestions || []);
    await db.transaction(['meta', 'cache'], async (s) => {
      if ((await db.requestValue(s.meta.get('context')))?.scope !== local.scope) return;
      s.cache.put({
        id: `${local.scope}:commerce`,
        scope: local.scope,
        purchases: ps.map((p) => ({ ...p, revisions: [] })),
        products: sk,
        expiry: ex.lots,
        expiry_as_of: ex.as_of,
        saved_at: Date.now(),
        expires_at: Date.now() + 86400000,
      });
    });
  }
  useEffect(() => {
    load().catch((e) => setError(e.message));
  }, []);
  useEffect(() => {
    if (initialRoute === '/stock/expiry') {
      setTab('expiry');
      return;
    }
    if (!initialRoute.startsWith('/stock/') || !products.length) return;
    const product = products.find((p) => p.id === initialRoute.split('/')[2]);
    if (product) {
      setTab('stock');
      api(`/products/${product.id}/movements`)
        .then((rows) => setMovements({ product, rows }))
        .catch((e) => setError(e.message));
    }
  }, [initialRoute, products.length]);
  async function run(fn) {
    setBusy(true);
    setError('');
    try {
      await fn();
      window.dispatchEvent(new Event('munafa-server-change'));
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  async function choose(p) {
    const v = navigator.onLine
      ? await api(`/purchases/${p.id}`)
      : purchases.find((x) => x.id === p.id);
    if (!v) throw new Error('No saved purchase. Connect to refresh it.');
    setSelected(v);
    setDraft(v.status === 'draft' ? v.draft : null);
    setFile(null);
    setText('');
    uploadAttempt.current = null;
    setDeviceSaved(null);
    setReceiving(null);
    setEditReceipt(null);
  }
  async function refreshPurchase(id) {
    await choose({ id });
    await load();
  }
  function update(k, v) {
    setDraft((d) => ({ ...d, [k]: v }));
  }
  function changeLine(i, k, v) {
    setDraft((d) => ({ ...d, lines: d.lines.map((l, j) => (j === i ? { ...l, [k]: v } : l)) }));
  }
  function startReceiving(r = null) {
    setEditReceipt(r);
    setReceiving(
      r
        ? r.payload
        : {
            purchase_version: selected.version,
            received_on: today(),
            delivery_complete: false,
            pricing_confirmed: false,
            lines: selected.lines.map((l) => ({
              purchase_line_id: l.id,
              quantity: null,
              damaged_quantity: '0',
              unit: l.unit,
              unit_confirmed: false,
              batch_reference: null,
              expiry_date: null,
            })),
          },
    );
  }
  const savedOnDevice =
    deviceSaved?.signature === JSON.stringify(draft) &&
    deviceSaved?.file === file &&
    deviceSaved?.text === text;
  const dirty =
    !!receiving ||
    (!savedOnDevice &&
      (!!file ||
        !!text.trim() ||
        (!!draft && JSON.stringify(draft) !== JSON.stringify(selected?.draft || fresh()))));
  useEffect(() => {
    window.dispatchEvent(new CustomEvent('munafa-unsaved-purchase', { detail: { dirty, busy } }));
    const warn = (event) => {
      if (dirty) {
        event.preventDefault();
        event.returnValue = '';
      }
    };
    window.addEventListener('beforeunload', warn);
    return () => {
      window.removeEventListener('beforeunload', warn);
      window.dispatchEvent(
        new CustomEvent('munafa-unsaved-purchase', { detail: { dirty: false } }),
      );
    };
  }, [dirty, busy]);
  function resetEditor(startNew) {
    setTab('purchases');
    setFile(null);
    setText('');
    setError('');
    setNotice('');
    setSelected(null);
    setDraft(startNew ? fresh() : null);
    setDraftId(crypto.randomUUID());
    setReceiving(null);
    setEditReceipt(null);
    setMovements(null);
    setMovement(null);
    setSku(null);
    uploadAttempt.current = null;
    setLeaveIntent(null);
    setDeviceSaved(null);
    setTimeout(() => editorTop.current?.scrollIntoView({ block: 'start', behavior: 'instant' }), 0);
  }
  function requestEditor(startNew) {
    if (busy) return;
    if (dirty) {
      setLeaveIntent(startNew ? 'new' : 'list');
      return;
    }
    resetEditor(startNew);
  }
  async function saveManualDocument() {
    const signature = JSON.stringify(draft);
    if (
      !uploadAttempt.current ||
      uploadAttempt.current.file !== file ||
      uploadAttempt.current.signature !== signature
    ) {
      const form = new FormData();
      form.append('file', file);
      form.append('manual_draft', signature);
      // Encode once so retries preserve the multipart boundary and request digest.
      const request = new Request(location.href, { method: 'POST', body: form });
      const contentType = request.headers.get('content-type');
      const body = await request.blob();
      uploadAttempt.current = { body, contentType, signature, file, key: crypto.randomUUID() };
    }
    const a = uploadAttempt.current;
    return api('/purchases/document', {
      method: 'POST',
      body: a.body,
      headers: { 'Idempotency-Key': a.key, 'Content-Type': a.contentType },
    });
  }
  const tabLabel = (key) => t({ purchases: 'Bills', stock: 'Stock', expiry: 'Expiry radar' }[key]);
  const actionsDisabled = busy || !navigator.onLine;
  return (
    <section className="commerce-workspace">
      <div className="page-heading">
        <div>
          <span className="eyebrow">YOUR SUPPLY DESK</span>
          <h1>{t('Deliveries & Stock')}</h1>
          <p>Review the bill first. Count the physical delivery separately.</p>
        </div>
        <button className="button primary" disabled={busy} onClick={() => requestEditor(true)}>
          <Plus size={17} aria-hidden="true" /> {t('Add new bill')}
        </button>
      </div>
      <ol className="delivery-steps" aria-label="Two steps for every delivery">
        <li>
          <strong>1 · {t('What the bill says')}</strong>
          <small>Check items, prices and quantities. Saving a bill does not add stock.</small>
        </li>
        <li>
          <strong>2 · {t('Count delivered items')}</strong>
          <small>Count what arrived. Only confirmed usable items go into stock.</small>
        </li>
      </ol>
      <div className="commerce-summary" aria-label="Purchase and stock summary">
        <div>
          <span>
            <FileText size={17} /> Saved bills
          </span>
          <strong>{purchases.length}</strong>
          <small>
            {purchases.filter((p) => p.status === 'draft').length} awaiting confirmation
          </small>
        </div>
        <div>
          <span>
            <Package size={17} /> Products tracked
          </span>
          <strong>{products.length}</strong>
          <small>{products.filter((p) => p.below_threshold).length} below reorder level</small>
        </div>
        <div>
          <span>
            <CalendarClock size={17} /> Expiry watch
          </span>
          <strong>{expiry.length}</strong>
          <small>Expired or due within 30 days</small>
        </div>
      </div>
      <div className="tabs commerce-tabs">
        {['purchases', 'stock', 'expiry'].map((t) => (
          <button
            className={tab === t ? 'chosen' : ''}
            key={t}
            aria-pressed={tab === t}
            onClick={() => setTab(t)}
          >
            {tabLabel(t)}
          </button>
        ))}
      </div>
      {error && (
        <div role="alert" className="error-box">
          {error}
        </div>
      )}
      {notice && <p role="status">{notice}</p>}
      <fieldset disabled={busy} style={{ border: 0, padding: 0, minWidth: 0 }}>
        {tab === 'purchases' && (
          <>
            {!draft && !selected && (
              <div className="panel">
                <h2>{t('Saved bills')}</h2>
                {!purchases.length && (
                  <p className="commerce-empty">No purchases yet. Add a bill to begin.</p>
                )}
                {purchases.map((p) => (
                  <button
                    className="supplier-case commerce-purchase-row"
                    key={p.id}
                    onClick={() => run(() => choose(p))}
                  >
                    <span className="commerce-row-icon">
                      <FileText size={19} aria-hidden="true" />
                    </span>
                    <span className="commerce-row-copy">
                      <strong>{p.draft.supplier || 'Supplier needs review'}</strong>
                      <small>
                        {p.draft.reference || 'No reference'} ·{' '}
                        {p.draft.date || 'Date needs review'}
                        {p.synthetic ? ' · Demo' : ''}
                      </small>
                    </span>
                    <span className="commerce-row-total">
                      <strong>{money(p.accepted_total_paise ?? p.draft.total_paise)}</strong>
                      <span className={`commerce-status ${p.status}`}>
                        {p.status === 'accepted' ? 'Confirmed' : 'Draft'}
                      </span>
                      {hasMissingItems(p) && (
                        <span className="badge partial">{t('Missing items')}</span>
                      )}
                    </span>
                    <ChevronRight size={17} aria-hidden="true" />
                  </button>
                ))}
              </div>
            )}
            {(draft || selected) && (
              <button className="text-button" onClick={() => requestEditor(false)}>
                {t('Back to saved bills')}
              </button>
            )}
            {draft && (
              <form
                className="panel"
                onSubmit={(e) => {
                  e.preventDefault();
                  run(async () => {
                    const p = selected
                      ? await api(`/purchases/${selected.id}`, {
                          method: 'PATCH',
                          body: { version: selected.version, draft },
                        })
                      : file
                        ? await saveManualDocument()
                        : text.trim()
                          ? await api('/purchases/extract-text', {
                              method: 'POST',
                              body: { text, manual_draft: draft },
                              headers: { 'Idempotency-Key': draftId },
                            })
                          : await api('/purchases/manual', {
                              method: 'POST',
                              body: draft,
                              headers: { 'Idempotency-Key': draftId },
                            });
                    await refreshPurchase(p.id);
                    setNotice('Draft saved. Review validation before acceptance.');
                  });
                }}
              >
                <h2 ref={editorTop} tabIndex={-1}>
                  {t('Review invoice')}
                </h2>
                <p>
                  Every proposed field needs merchant review. Received quantities are entered later.
                </p>
                {!selected && (
                  <>
                    <Field label="Bill photo or PDF">
                      <input
                        type="file"
                        accept="image/png,image/jpeg,image/webp,application/pdf"
                        onChange={(e) => setFile(e.target.files[0])}
                      />
                    </Field>
                    <button
                      type="button"
                      className="button secondary"
                      disabled={actionsDisabled || !file}
                      onClick={() =>
                        run(async () => {
                          const f = new FormData();
                          f.append('file', file);
                          const p = await api('/purchases/document', { method: 'POST', body: f });
                          await refreshPurchase(p.id);
                        })
                      }
                    >
                      Read document
                    </button>
                    <Field label="Paste bill text">
                      <textarea
                        maxLength={18000}
                        value={text}
                        onChange={(e) => setText(e.target.value)}
                      />
                    </Field>
                    <button
                      type="button"
                      className="button secondary"
                      disabled={actionsDisabled || !text}
                      onClick={() =>
                        run(async () => {
                          const p = await api('/purchases/extract-text', {
                            method: 'POST',
                            body: { text },
                          });
                          await refreshPurchase(p.id);
                        })
                      }
                    >
                      Read text
                    </button>
                    <button
                      type="button"
                      className="button secondary"
                      disabled={actionsDisabled}
                      onClick={() =>
                        run(async () => {
                          const p = await api('/purchases/sample', { method: 'POST' });
                          await refreshPurchase(p.id);
                        })
                      }
                    >
                      Load demo purchase
                    </button>
                  </>
                )}
                <div className="form-grid">
                  <Input
                    label="Supplier"
                    value={draft.supplier}
                    change={(v) => update('supplier', v)}
                  />
                  <Input
                    label="Invoice reference"
                    value={draft.reference}
                    change={(v) => update('reference', v)}
                  />
                  <Input
                    label="Invoice date"
                    type="date"
                    value={draft.date}
                    change={(v) => update('date', v)}
                  />
                </div>
                <p className="workflow-step">
                  <strong>Step 1 · Check the paper bill</strong>
                  <br />
                  Confirm billed quantities and prices. Count what arrived separately after
                  confirming the bill.
                </p>
                {draft.lines.map((l, i) => (
                  <div className="panel" key={i}>
                    <h3>Item {i + 1}</h3>
                    <div className="form-grid">
                      <Input
                        label="Description"
                        value={l.description}
                        change={(v) => changeLine(i, 'description', v)}
                      />
                      <Field label="Reviewed Item">
                        <select
                          value={l.product_id || ''}
                          onChange={(e) => changeLine(i, 'product_id', e.target.value || null)}
                        >
                          <option value="">Choose a Item from Stock</option>
                          {products.map((p) => (
                            <option key={p.id} value={p.id}>
                              {p.name} ({p.unit})
                            </option>
                          ))}
                        </select>
                      </Field>
                      <Input
                        label="Billed quantity"
                        value={l.billed_quantity}
                        change={(v) => changeLine(i, 'billed_quantity', v || null)}
                      />
                      <Unit value={l.unit} change={(v) => changeLine(i, 'unit', v)} />
                      <MoneyInput
                        label="Unit price (₹)"
                        value={l.unit_price_paise}
                        change={(v) => changeLine(i, 'unit_price_paise', v)}
                      />
                      <MoneyInput
                        label="Claim price per unit (₹)"
                        value={l.effective_price_paise}
                        change={(v) => changeLine(i, 'effective_price_paise', v)}
                      />
                    </div>
                    <p>{l.review_note || 'Check this item against the bill.'}</p>
                    {draft.lines.length > 1 && (
                      <button
                        type="button"
                        onClick={() =>
                          update(
                            'lines',
                            draft.lines.filter((_, j) => i !== j),
                          )
                        }
                      >
                        Remove item
                      </button>
                    )}
                  </div>
                ))}
                <button type="button" onClick={() => update('lines', [...draft.lines, line()])}>
                  Add item
                </button>
                <MoneyInput
                  label="Invoice total (₹)"
                  value={draft.total_paise}
                  change={(v) => update('total_paise', v)}
                />
                <details className="bill-details">
                  <summary>More bill details · Tax, discount and rounding</summary>
                  <div className="form-grid">
                    {[
                      ['subtotal_paise', 'Subtotal'],
                      ['tax_paise', 'Tax'],
                      ['discount_paise', 'Discount'],
                      ['rounding_paise', 'Rounding'],
                    ].map(([k, label]) => (
                      <MoneyInput
                        key={k}
                        label={`${label} (₹)`}
                        value={draft[k]}
                        signed={k === 'rounding_paise'}
                        change={(v) => update(k, v)}
                      />
                    ))}
                  </div>
                </details>
                <button className="button primary" disabled={actionsDisabled}>
                  {t('Save invoice draft')}
                </button>
                {!selected && (
                  <button
                    type="button"
                    className="button secondary"
                    onClick={() =>
                      run(async () => {
                        await db.saveDraft(
                          local.scope,
                          {
                            id: draftId,
                            kind: 'purchase',
                            payload: { draft, ...(text.trim() ? { source_text: text } : {}) },
                          },
                          file,
                        );
                        await local.refresh();
                        setDeviceSaved({ signature: JSON.stringify(draft), file, text });
                        setNotice(
                          'Saved on this device. Open Offline drafts to review and queue it.',
                        );
                      })
                    }
                  >
                    {t('Save purchase on device')}
                  </button>
                )}
              </form>
            )}
            {selected && (
              <div className="panel">
                <h2>
                  {selected.draft.reference} · {selected.status}
                </h2>
                <p>
                  {selected.synthetic ? 'Synthetic demo · ' : ''}
                  {selected.draft.supplier} ·{' '}
                  {money(selected.accepted_total_paise ?? selected.draft.total_paise)}
                </p>
                {selected.status === 'draft' && (
                  <p className="info-box">
                    Check the bill details before confirming. Enter delivered quantities separately.
                  </p>
                )}
                {selected.documents.map((d) => (
                  <div key={d.id}>
                    <DocumentPreview document={d} />
                    <button
                      className="text-button"
                      key={d.id}
                      onClick={() =>
                        run(() => downloadPrivate(`/api/purchase-documents/${d.id}`, d.name))
                      }
                    >
                      Open original: {d.name}
                    </button>
                  </div>
                ))}
                {selected.checks.issues.map((s, i) => (
                  <p key={i} role="note">
                    {s.replace('reviewed SKU mapping', 'reviewed stock item')}
                  </p>
                ))}
                {selected.checks.warnings.map((s, i) => (
                  <p key={i}>
                    {s
                      .replace(
                        'extraction confidence not supplied; merchant review required',
                        'check this item against the original bill',
                      )
                      .replace('reviewed SKU mapping', 'reviewed stock item')}
                  </p>
                ))}
                {selected.status === 'draft' && (
                  <button
                    className="button primary"
                    disabled={
                      actionsDisabled ||
                      !selected.checks.eligible ||
                      JSON.stringify(draft) !== JSON.stringify(selected.draft)
                    }
                    onClick={() =>
                      run(async () => {
                        await proposeCommerceAction(
                          'accept_purchase',
                          selected.id,
                          selected.version,
                        );
                        await refreshPurchase(selected.id);
                      })
                    }
                  >
                    Save checked bill · stock stays the same
                  </button>
                )}
                {selected.status === 'accepted' && (
                  <>
                    <h3>Accepted bill lines</h3>
                    {selected.lines.map((l) => (
                      <p key={l.id}>
                        {l.description}: billed {l.billed_quantity} {l.unit}, physically received{' '}
                        {l.received_quantity} {l.unit} · {l.receiving_state}
                      </p>
                    ))}
                    {!selected.delivery_complete && (
                      <button className="button primary" onClick={() => startReceiving()}>
                        {t('Count delivered items')}
                      </button>
                    )}
                    {selected.receiving_drafts.map((r) => (
                      <div key={r.id}>
                        <span>
                          Receiving {r.id.slice(0, 8)} · {r.status}
                        </span>
                        {r.status === 'draft' && (
                          <button onClick={() => startReceiving(r)}>Review receiving draft</button>
                        )}
                      </div>
                    ))}
                    {selected.receipts.map((r) => (
                      <p key={r.id}>
                        Accepted receipt · {r.accepted_at} ·{' '}
                        {r.delivery_complete
                          ? 'Final delivery'
                          : 'Partial delivery, remaining goods expected'}
                      </p>
                    ))}
                    <button
                      className="button secondary"
                      disabled={busy || openingCase}
                      onClick={async () => {
                        setOpeningCase(true);
                        setError('');
                        try {
                          openCase(await api(`/cases/${selected.case_id}`));
                        } catch (e) {
                          setError(e.message);
                        } finally {
                          setOpeningCase(false);
                        }
                      }}
                    >
                      {openingCase ? 'Opening recovery case…' : 'Open supplier recovery case'}
                    </button>
                  </>
                )}
              </div>
            )}
            {receiving && (
              <form
                className="panel"
                onSubmit={(e) => {
                  e.preventDefault();
                  run(async () => {
                    if (editReceipt)
                      await api(`/receivings/${editReceipt.id}`, {
                        method: 'PATCH',
                        body: { version: editReceipt.version, payload: receiving },
                      });
                    else
                      await api(`/purchases/${selected.id}/receivings`, {
                        method: 'POST',
                        body: receiving,
                      });
                    await refreshPurchase(selected.id);
                    setNotice(
                      'Receiving draft saved. Review and explicitly accept it to update stock.',
                    );
                  });
                }}
              >
                <h2>{t('Count delivered items')}</h2>
                <p className="workflow-step">
                  Step 2 · Count what actually arrived. The bill does not confirm delivery.
                </p>
                <p>
                  Enter quantities in this delivery only. Damaged units do not enter usable stock.
                </p>
                <Input
                  label="Received on"
                  type="date"
                  value={receiving.received_on}
                  change={(v) => setReceiving({ ...receiving, received_on: v })}
                />
                {receiving.lines.map((l, i) => {
                  const change = (k, v) =>
                    setReceiving({
                      ...receiving,
                      lines: receiving.lines.map((x, j) =>
                        i === j
                          ? { ...x, [k]: v, ...(k === 'unit' ? { unit_confirmed: false } : {}) }
                          : x,
                      ),
                    });
                  return (
                    <div className="panel" key={l.purchase_line_id}>
                      <h3>
                        {selected.lines.find((x) => x.id === l.purchase_line_id)?.description}
                      </h3>
                      <div className="form-grid">
                        <Input
                          label="Actual quantity"
                          value={l.quantity}
                          change={(v) => change('quantity', v || null)}
                        />
                        <Input
                          label="Damaged quantity"
                          value={l.damaged_quantity}
                          change={(v) => change('damaged_quantity', v)}
                        />
                        <Unit
                          value={l.unit}
                          change={(v) => {
                            change('unit', v);
                          }}
                        />
                        <Input
                          label="Batch reference"
                          value={l.batch_reference}
                          change={(v) => change('batch_reference', v || null)}
                        />
                        <Input
                          label="Expiry date"
                          type="date"
                          value={l.expiry_date}
                          change={(v) => change('expiry_date', v || null)}
                        />
                      </div>
                      <label>
                        <input
                          type="checkbox"
                          checked={l.unit_confirmed}
                          onChange={(e) => change('unit_confirmed', e.target.checked)}
                        />
                        I checked the units.
                      </label>
                    </div>
                  );
                })}
                <label className="check-field">
                  <input
                    type="checkbox"
                    checked={receiving.delivery_complete}
                    onChange={(e) =>
                      setReceiving({ ...receiving, delivery_complete: e.target.checked })
                    }
                  />
                  Delivery is complete
                </label>
                <label className="check-field">
                  <input
                    type="checkbox"
                    checked={receiving.pricing_confirmed}
                    onChange={(e) =>
                      setReceiving({ ...receiving, pricing_confirmed: e.target.checked })
                    }
                  />
                  Effective prices verified
                </label>
                <button className="button primary" disabled={actionsDisabled}>
                  Save receiving draft
                </button>
                <button
                  type="button"
                  className="button secondary"
                  onClick={() =>
                    run(async () => {
                      await db.saveDraft(local.scope, {
                        id: crypto.randomUUID(),
                        kind: 'purchase_receiving',
                        entity_id: selected.id,
                        expected_version: selected.version,
                        payload: receiving,
                      });
                      await local.refresh();
                      setNotice(
                        'Receiving saved on device; stock unchanged until server approval.',
                      );
                    })
                  }
                >
                  Save receiving on device
                </button>
                {editReceipt && (
                  <button
                    type="button"
                    className="button primary"
                    disabled={
                      actionsDisabled ||
                      JSON.stringify(receiving) !== JSON.stringify(editReceipt.payload)
                    }
                    onClick={() =>
                      run(async () => {
                        await proposeCommerceAction(
                          'accept_receiving',
                          editReceipt.id,
                          editReceipt.version,
                        );
                        await refreshPurchase(selected.id);
                      })
                    }
                  >
                    Accept reviewed receiving and update stock
                  </button>
                )}
              </form>
            )}
          </>
        )}
        {tab === 'stock' && (
          <div className="panel">
            <h2>Item catalogue & confirmed stock</h2>
            {reorders.length > 0 && (
              <div
                className="panel"
                style={{
                  border: '2px solid #e53935',
                  borderRadius: '8px',
                  padding: '1rem',
                  marginBottom: '1.25rem',
                  background: '#fffbfa',
                }}
              >
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    flexWrap: 'wrap',
                  }}
                >
                  <h3 style={{ margin: 0, color: '#c62828' }}>
                    ⚠️ Smart Low-Stock Reorder ({reorders.length} Item
                    {reorders.length !== 1 ? 's' : ''})
                  </h3>
                  <span className="badge badge-warn" style={{ fontWeight: 'bold' }}>
                    Action Needed
                  </span>
                </div>
                <p className="tiny-help" style={{ margin: '0.4rem 0 0.8rem' }}>
                  Calculated from merchant reorder threshold and latest accepted invoice prices.
                  1-tap WhatsApp formats a draft purchase order.
                </p>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                  {reorders.map((item) => (
                    <div
                      key={item.product_id}
                      style={{
                        background: '#fff',
                        border: '1px solid #ffcdd2',
                        borderRadius: '6px',
                        padding: '0.85rem',
                      }}
                    >
                      <div
                        style={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'flex-start',
                          flexWrap: 'wrap',
                          gap: '0.5rem',
                        }}
                      >
                        <div>
                          <strong style={{ fontSize: '1rem' }}>{item.product_name}</strong>
                          <div style={{ fontSize: '0.85rem', color: '#666', marginTop: '0.2rem' }}>
                            {item.stock_quantity} {item.unit} remaining (threshold:{' '}
                            {item.reorder_threshold})
                          </div>
                        </div>
                        <span
                          className="badge badge-warn"
                          style={{ fontWeight: 'bold', fontSize: '0.9rem' }}
                        >
                          Recommended: {item.recommended_reorder_qty} {item.unit}
                          {item.estimated_cost_paise
                            ? ` (~${money(item.estimated_cost_paise)})`
                            : ''}
                        </span>
                      </div>

                      <div style={{ fontSize: '0.85rem', marginTop: '0.5rem', color: '#444' }}>
                        <strong>Preferred Supplier:</strong> {item.preferred_supplier}
                        {item.last_price_paise
                          ? ` (Last billed: ${money(item.last_price_paise)}/${item.unit}${item.last_billed_date ? ` on ${item.last_billed_date}` : ''})`
                          : ''}
                      </div>

                      <div
                        style={{
                          marginTop: '0.75rem',
                          display: 'flex',
                          gap: '0.5rem',
                          alignItems: 'center',
                          flexWrap: 'wrap',
                        }}
                      >
                        <a
                          className="button primary"
                          href={item.whatsapp_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{
                            textDecoration: 'none',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '0.4rem',
                          }}
                        >
                          📲 Draft Order on WhatsApp
                        </a>
                        <details style={{ fontSize: '0.85rem', color: '#666' }}>
                          <summary style={{ cursor: 'pointer' }}>Preview PO Message</summary>
                          <pre
                            style={{
                              background: '#f5f5f5',
                              padding: '0.5rem',
                              borderRadius: '4px',
                              whiteSpace: 'pre-wrap',
                              marginTop: '0.3rem',
                              fontSize: '0.8rem',
                            }}
                          >
                            {item.po_message}
                          </pre>
                        </details>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
            <button
              className="button primary"
              onClick={() =>
                setSku({
                  code: '',
                  name: '',
                  unit: 'piece',
                  reorder_threshold: null,
                  expiry_tracking: false,
                })
              }
            >
              New Item
            </button>
            {products.map((p) => (
              <div className="panel commerce-stock-card" key={p.id}>
                <div className="commerce-stock-title">
                  <span className="commerce-row-icon">
                    <Package size={20} aria-hidden="true" />
                  </span>
                  <div>
                    <strong>{p.name}</strong>
                    <small>
                      {p.code} · {p.unit}
                    </small>
                  </div>
                </div>
                <p className="commerce-stock-balance">
                  {p.stock_quantity} {p.unit} · Saved stock count{' '}
                  {p.below_threshold ? <span className="badge review">{t('Low stock')}</span> : ''}
                </p>
                <button
                  onClick={() =>
                    run(async () =>
                      setMovements({ product: p, rows: await api(`/products/${p.id}/movements`) }),
                    )
                  }
                >
                  Stock changes
                </button>
                <button onClick={() => setSku(p)}>Edit item</button>
                <button
                  onClick={() =>
                    setMovement({
                      product_id: p.id,
                      expected_stock_version: p.stock_version,
                      kind: 'count',
                      quantity: '0',
                      unit: p.unit,
                      reference: '',
                      occurred_on: today(),
                      reason: '',
                    })
                  }
                >
                  Record stock movement
                </button>
              </div>
            ))}
            {!products.length && (
              <p className="commerce-empty">Create a Item before accepting invoice lines.</p>
            )}
            {sku && (
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  run(async () => {
                    const body = {
                      code: sku.code,
                      name: sku.name,
                      unit: sku.unit,
                      barcode: sku.barcode || null,
                      reorder_threshold: sku.reorder_threshold || null,
                      expiry_tracking: sku.expiry_tracking,
                    };
                    await api(sku.id ? `/products/${sku.id}` : '/products', {
                      method: sku.id ? 'PATCH' : 'POST',
                      body: sku.id ? { version: sku.version, product: body } : body,
                    });
                    setSku(null);
                    await load();
                  });
                }}
              >
                <h3>Item details</h3>
                {['code', 'name', 'barcode', 'reorder_threshold'].map((k) => (
                  <Input
                    key={k}
                    label={k}
                    value={sku[k]}
                    change={(v) => setSku({ ...sku, [k]: v })}
                  />
                ))}
                <Unit value={sku.unit} change={(v) => setSku({ ...sku, unit: v })} />
                <label>
                  <input
                    type="checkbox"
                    checked={sku.expiry_tracking}
                    onChange={(e) => setSku({ ...sku, expiry_tracking: e.target.checked })}
                  />
                  Track expiry
                </label>
                <button className="button primary" disabled={actionsDisabled}>
                  Save Item
                </button>
              </form>
            )}
            {movements && (
              <div>
                <h3>
                  {movements.product.name} · movement history ({movements.product.unit})
                </h3>
                {movements.rows.events.map((event) => (
                  <article className="panel" key={event.id}>
                    <strong>
                      {event.kind}: {event.quantity_delta} {movements.product.unit}
                    </strong>
                    <p>
                      {event.occurred_on} · {event.reference}
                    </p>
                    <p>{event.reason}</p>
                  </article>
                ))}
                {!movements.rows.events.length && <p>No accepted stock movements.</p>}
                <ConversionForm
                  product={movements.product}
                  onSave={() =>
                    setNotice(
                      'Merchant-defined conversion saved. Review invoice units before acceptance.',
                    )
                  }
                />
                {movements.rows.lots.map((lot) => (
                  <p key={lot.id}>
                    Batch {lot.batch_reference || lot.id}: {lot.quantity} {movements.product.unit} ·
                    expiry {lot.expiry_date || 'not recorded'}
                  </p>
                ))}
              </div>
            )}
            {movement && (
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  run(async () => {
                    await proposeCommerceAction(
                      'inventory_movement',
                      movement.product_id,
                      movement.expected_stock_version,
                      movement,
                    );
                    setMovement(null);
                    await load();
                  });
                }}
              >
                <h3>Review stock movement</h3>
                <Field label="Movement type">
                  <select
                    value={movement.kind}
                    onChange={(e) => setMovement({ ...movement, kind: e.target.value })}
                  >
                    {[
                      'count',
                      'sale',
                      'return_in',
                      'return_out',
                      'damage',
                      'reversal',
                      'shortage_correction',
                    ].map((k) => (
                      <option key={k}>{k}</option>
                    ))}
                  </select>
                </Field>
                {[
                  'quantity',
                  'reference',
                  'reason',
                  'lot_id',
                  'batch_reference',
                  'expiry_date',
                  'reversal_of',
                  'case_id',
                ].map((k) => (
                  <Input
                    key={k}
                    label={k}
                    value={movement[k]}
                    change={(v) => setMovement({ ...movement, [k]: v || undefined })}
                  />
                ))}
                <button className="button primary" disabled={actionsDisabled}>
                  Approve stock movement
                </button>
                <button
                  type="button"
                  onClick={() =>
                    run(async () => {
                      await db.saveDraft(local.scope, {
                        id: crypto.randomUUID(),
                        kind: 'inventory_movement',
                        entity_id: movement.product_id,
                        expected_version: movement.expected_stock_version,
                        payload: { movement, merchant_confirmed: true },
                      });
                      await local.refresh();
                      setNotice('Reviewed stock movement saved locally; queue explicitly to sync.');
                    })
                  }
                >
                  Save reviewed movement on device
                </button>
              </form>
            )}
          </div>
        )}
        {tab === 'expiry' &&
          (expiryLoaded ? (
            <ExpiryRadar lots={expiry} asOf={expiryAsOf} stale={expiryStale || !navigator.onLine} />
          ) : (
            <p role="status">
              {error ||
                (!navigator.onLine
                  ? 'Reconnect to load recorded batches.'
                  : 'Loading recorded batches…')}{' '}
              <button onClick={() => load().catch((e) => setError(e.message))}>
                Refresh expiry
              </button>
            </p>
          ))}
      </fieldset>
      {leaveIntent && (
        <Modal
          title="Keep your current work?"
          subtitle="These edits have not been saved. Starting another bill or leaving this editor will discard them."
          close={() => setLeaveIntent(null)}
        >
          <div className="modal-body">
            <button className="button primary full" onClick={() => setLeaveIntent(null)}>
              {t('Continue current bill')}
            </button>
            <button
              className="button secondary full"
              onClick={() => resetEditor(leaveIntent === 'new')}
            >
              {leaveIntent === 'new'
                ? t('Discard and start new bill')
                : 'Discard edits and view saved bills'}
            </button>
            <p>
              To keep a copy first, continue editing and choose Save purchase on device or Save
              invoice draft.
            </p>
          </div>
        </Modal>
      )}
    </section>
  );
}
