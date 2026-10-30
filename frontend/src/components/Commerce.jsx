import React, { useState, useEffect } from 'react';
import { api, money, today, downloadPrivate, proposeCommerceAction } from '../api';
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
      <p>Saved device draft; server validation and source version checks still apply.</p>
      <div className="form-grid">
        {fields.map((k) => (
          <Input
            key={k}
            label={k.replaceAll('_', ' ')}
            value={d[k]}
            change={(v) =>
              set({ ...d, [k]: k.endsWith('_paise') ? (v === '' ? null : Number(v)) : v })
            }
          />
        ))}
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
              ? [
                  'description',
                  'product_id',
                  'billed_quantity',
                  'unit_price_paise',
                  'effective_price_paise',
                ]
              : ['quantity', 'damaged_quantity', 'batch_reference', 'expiry_date']
            ).map((k) => (
              <Input
                key={k}
                label={k.replaceAll('_', ' ')}
                value={l[k]}
                change={(v) =>
                  update(k, k.endsWith('_paise') ? (v === '' ? null : Number(v)) : v || null)
                }
              />
            ))}
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
  return (
    <label className="field">
      {label}
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
export function Commerce({ openCase }) {
  const local = useOffline();
  const [tab, setTab] = useState('purchases'),
    [purchases, setPurchases] = useState([]),
    [products, setProducts] = useState([]),
    [expiry, setExpiry] = useState([]),
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
        setNotice('Device snapshot: stock may have changed. Acceptance requires a connection.');
      }
      return;
    }
    const [ps, sk, ex] = await Promise.all([
      api('/purchases'),
      api('/products'),
      api('/inventory/expiry'),
    ]);
    setPurchases(ps);
    setProducts(sk);
    setExpiry(ex.lots);
    await db.transaction(['meta', 'cache'], async (s) => {
      if ((await db.requestValue(s.meta.get('context')))?.scope !== local.scope) return;
      s.cache.put({
        id: `${local.scope}:commerce`,
        scope: local.scope,
        purchases: ps.map((p) => ({ ...p, revisions: [] })),
        products: sk,
        expiry: ex.lots,
        saved_at: Date.now(),
        expires_at: Date.now() + 86400000,
      });
    });
  }
  useEffect(() => {
    load().catch((e) => setError(e.message));
  }, []);
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
  const actionsDisabled = busy || !navigator.onLine;
  return (
    <section className="commerce-workspace">
      <div className="page-heading">
        <div>
          <h1>Purchases & stock</h1>
          <p>Review the bill first. Count the physical delivery separately.</p>
        </div>
        <button
          className="button primary"
          onClick={() => {
            setSelected(null);
            setDraft(fresh());
            setDraftId(crypto.randomUUID());
            setReceiving(null);
          }}
        >
          New purchase
        </button>
      </div>
      <div className="tabs">
        {['purchases', 'stock', 'expiry'].map((t) => (
          <button
            key={t}
            onClick={() => {
              setTab(t);
              setSelected(null);
              setDraft(null);
              setReceiving(null);
            }}
          >
            {t}
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
                <h2>Purchase register</h2>
                {!purchases.length && <p>No purchases yet. Add a bill to begin.</p>}
                {purchases.map((p) => (
                  <button className="supplier-case" key={p.id} onClick={() => run(() => choose(p))}>
                    {p.synthetic ? 'DEMO · ' : ''}
                    {p.draft.supplier || 'Supplier needs review'} ·{' '}
                    {p.draft.reference || 'No reference'} · {p.draft.date} · {p.status} ·{' '}
                    {money(p.accepted_total_paise ?? p.draft.total_paise)}
                  </button>
                ))}
              </div>
            )}
            {(draft || selected) && (
              <button
                className="text-button"
                onClick={() => {
                  setSelected(null);
                  setDraft(null);
                  setReceiving(null);
                }}
              >
                Back to purchase register
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
                      : await api('/purchases/manual', { method: 'POST', body: draft });
                    await refreshPurchase(p.id);
                    setNotice('Draft saved. Review validation before acceptance.');
                  });
                }}
              >
                <h2>Review invoice</h2>
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
                      <textarea value={text} onChange={(e) => setText(e.target.value)} />
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
                {draft.lines.map((l, i) => (
                  <div className="panel" key={i}>
                    <h3>Item {i + 1}</h3>
                    <div className="form-grid">
                      <Input
                        label="Description"
                        value={l.description}
                        change={(v) => changeLine(i, 'description', v)}
                      />
                      <Field label="Reviewed SKU">
                        <select
                          value={l.product_id || ''}
                          onChange={(e) => changeLine(i, 'product_id', e.target.value || null)}
                        >
                          <option value="">Choose a SKU from Stock</option>
                          {products.map((p) => (
                            <option key={p.id} value={p.id}>
                              {p.name} ({p.unit})
                            </option>
                          ))}
                        </select>
                      </Field>
                      <Input
                        label="Billed quantity (decimal)"
                        value={l.billed_quantity}
                        change={(v) => changeLine(i, 'billed_quantity', v || null)}
                      />
                      <Unit value={l.unit} change={(v) => changeLine(i, 'unit', v)} />
                      <Input
                        label="Printed unit price (paise)"
                        value={l.unit_price_paise}
                        change={(v) =>
                          changeLine(i, 'unit_price_paise', v === '' ? null : Number(v))
                        }
                      />
                      <Input
                        label="Effective claim unit price (paise)"
                        value={l.effective_price_paise}
                        change={(v) =>
                          changeLine(i, 'effective_price_paise', v === '' ? null : Number(v))
                        }
                      />
                    </div>
                    <p>
                      {l.review_note || 'Check the original bill.'}{' '}
                      {l.confidence == null
                        ? 'Confidence unavailable; review required.'
                        : `Extraction score: ${l.confidence}; review required.`}
                    </p>
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
                <div className="form-grid">
                  {[
                    ['subtotal_paise', 'Subtotal'],
                    ['tax_paise', 'Tax'],
                    ['discount_paise', 'Discount'],
                    ['rounding_paise', 'Rounding'],
                    ['total_paise', 'Invoice total'],
                  ].map(([k, label]) => (
                    <Input
                      key={k}
                      label={`${label} (paise)`}
                      value={draft[k]}
                      change={(v) => update(k, v === '' ? null : Number(v))}
                    />
                  ))}
                </div>
                <button className="button primary" disabled={actionsDisabled}>
                  Save invoice draft
                </button>
                {!selected && (
                  <button
                    type="button"
                    className="button secondary"
                    onClick={() =>
                      run(async () => {
                        await db.saveDraft(
                          local.scope,
                          { id: draftId, kind: 'purchase', payload: { draft } },
                          file,
                        );
                        await local.refresh();
                        setNotice('Saved on this device. Queue from Drafts & sync.');
                      })
                    }
                  >
                    Save purchase on device
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
                    {s}
                  </p>
                ))}
                {selected.checks.warnings.map((s, i) => (
                  <p key={i}>{s}</p>
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
                    Confirm reviewed invoice (no stock change)
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
                        Record physical delivery
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
                      onClick={() =>
                        run(async () => openCase(await api(`/cases/${selected.case_id}`)))
                      }
                    >
                      Open supplier recovery case
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
                <h2>Physical receiving</h2>
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
            <h2>SKU catalogue & confirmed stock</h2>
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
              New SKU
            </button>
            {products.map((p) => (
              <div className="panel" key={p.id}>
                <strong>{p.name}</strong>
                <p>
                  {p.stock_quantity} {p.unit} · {p.stock_state}{' '}
                  {p.below_threshold ? '· REORDER' : ''}
                </p>
                <button
                  onClick={() =>
                    run(async () =>
                      setMovements({ product: p, rows: await api(`/products/${p.id}/movements`) }),
                    )
                  }
                >
                  Movement timeline
                </button>
                <button onClick={() => setSku(p)}>Edit SKU</button>
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
            {!products.length && <p>Create a SKU before accepting invoice lines.</p>}
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
                <h3>SKU details</h3>
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
                  Save SKU
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
                    <small>
                      Source {event.source_entity_id} · actor {event.actor_id} · operation{' '}
                      {event.operation_id}
                    </small>
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
        {tab === 'expiry' && (
          <div className="panel">
            <h2>Expired & expiring within 30 days</h2>
            {!expiry.length && <p>No recorded lots in this window.</p>}
            {expiry.map((l) => (
              <p key={l.id}>
                {l.product_name} · {l.quantity} {l.unit} · {l.expiry_date} ·{' '}
                {l.expired ? 'EXPIRED' : 'Expiring soon'}
              </p>
            ))}
          </div>
        )}
      </fieldset>
    </section>
  );
}
