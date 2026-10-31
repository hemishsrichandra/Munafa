import React, { useState, useEffect, useRef } from 'react';
import { ArrowRight, Plus, ShieldCheck, X, Upload, Sparkles, AlertCircle } from 'lucide-react';
import { useLanguage } from '../language';
import { paiseFromInput, api, today } from '../api';
import { icon, Modal, ErrorBox, Busy } from './ui';

const freshLine = () => ({
  name: '',
  billed: 1,
  unit: 'pack',
  price_paise: 0,
  received: null,
  received_unit: 'unknown',
  unit_confirmed: false,
  note: '',
});
const freshInvoice = () => ({
  supplier: '',
  supplier_phone: '',
  reference: '',
  date: today(),
  pricing_note: 'Verify effective prices after taxes, discounts and schemes.',
  lines: [freshLine()],
});
function InvoiceModal({ close, create, config }) {
  const { t } = useLanguage();
  const [tab, setTab] = useState('sample'),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(''),
    [invoice, setInvoice] = useState(freshInvoice),
    [text, setText] = useState(''),
    [file, setFile] = useState(null);
  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      let data;
      if (tab === 'sample') data = await api('/invoices/sample', { method: 'POST' });
      else if (tab === 'manual')
        data = await api('/invoices/manual', { method: 'POST', body: invoice });
      else if (tab === 'text')
        data = await api('/invoices/extract-text', { method: 'POST', body: { text } });
      else {
        const f = new FormData();
        f.append('file', file);
        data = await api('/invoices/extract', { method: 'POST', body: f });
      }
      create(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <Modal
      title={t('Add new bill')}
      subtitle="Step 1: Add the bill. Step 2: Count what arrived."
      close={close}
      closeDisabled={busy}
      wide
    >
      <form onSubmit={submit}>
        <div className="modal-body">
          <div className="intake-tabs">
            {[
              ['sample', 'Try a sample'],
              ['photo', 'Bill photo'],
              ['text', 'Paste bill text'],
              ['manual', 'Enter manually'],
            ].map(([id, t]) => (
              <button
                type="button"
                key={id}
                onClick={() => {
                  setTab(id);
                  setError('');
                }}
                className={tab === id ? 'selected' : ''}
              >
                {t}
              </button>
            ))}
          </div>
          {tab === 'sample' && (
            <div className="sample-intake">
              <div className="sample-paper">
                <div className="eyebrow">SYNTHETIC INVOICE</div>
                <h3>Shree Ganesh Distributors</h3>
                <div className="paper-sub">Invoice A-104 · 29 October 2026</div>
                {[
                  ['Parle-G biscuits', '12 packs', '₹40'],
                  ['Tata Tea 250 g', '6 packs', '₹125'],
                  ['Lifebuoy soap', '24 · unit unclear', '₹35'],
                ].map((r) => (
                  <div className="sample-line" key={r[0]}>
                    <strong>{r[0]}</strong>
                    <span>{r[1]}</span>
                    <span>{r[2]}</span>
                  </div>
                ))}
                <div className="sample-hint">
                  <Sparkles size={16} /> Can you spot the two missing biscuit packs?
                </div>
              </div>
              <p>
                Built from the pitch example. No tax, discount or scheme. The soap unit needs your
                review before the claim can be approved.
              </p>
            </div>
          )}
          {(tab === 'photo' || tab === 'text') && (
            <>
              <div className={`info-box ${config?.sarvam_configured ? '' : 'warm'}`}>
                <Sparkles size={18} />
                <p>
                  {config?.sarvam_configured
                    ? 'AI can help fill in the bill. Check each field before continuing.'
                    : 'Automatic bill reading is unavailable. Enter the details manually or try a sample.'}
                </p>
              </div>
              {tab === 'photo' ? (
                <label className="upload-zone">
                  <Upload size={30} />
                  <strong>{file ? file.name : 'Choose a clear bill photo'}</strong>
                  <span>PNG, JPEG or WebP · up to 8 MB</span>
                  <input
                    type="file"
                    accept="image/png,image/jpeg,image/webp"
                    required
                    onChange={(e) => setFile(e.target.files[0])}
                  />
                </label>
              ) : (
                <label className="field">
                  Invoice text
                  <textarea
                    required
                    minLength={20}
                    maxLength={18000}
                    rows={9}
                    value={text}
                    onChange={(e) => setText(e.target.value)}
                    placeholder={
                      'Shree Ganesh Distributors\nInvoice A-104, 29 October 2026\nBiscuits: 12 packs at INR 40 each\n...'
                    }
                  />
                </label>
              )}
            </>
          )}
          {tab === 'manual' && <InvoiceFields invoice={invoice} change={setInvoice} />}
          <ErrorBox text={error} />
        </div>
        <div className="modal-footer">
          <span>{icon(ShieldCheck, 15)} Nothing is sent to a supplier.</span>
          <button
            className="button primary"
            disabled={busy || ((tab === 'photo' || tab === 'text') && !config?.sarvam_configured)}
          >
            <Busy busy={busy}>
              {tab === 'sample'
                ? 'Use sample invoice'
                : tab === 'manual'
                  ? 'Create draft case'
                  : 'Read with Sarvam AI'}{' '}
              <ArrowRight size={16} />
            </Busy>
          </button>
        </div>
      </form>
    </Modal>
  );
}
function InvoiceFields({ invoice, change, review = false, draft = false }) {
  const update = (key, value) => change({ ...invoice, [key]: value });
  const lineChange = (index, key, value) => {
    const lines = invoice.lines.map((l, i) =>
      i === index
        ? {
            ...l,
            [key]: value,
            ...(key === 'unit' || key === 'received_unit' ? { unit_confirmed: false } : {}),
          }
        : l,
    );
    update('lines', lines);
  };
  return (
    <>
      <div className="form-grid">
        <label className="field">
          Supplier name
          <input
            required={!draft}
            value={invoice.supplier}
            maxLength={100}
            onChange={(e) => update('supplier', e.target.value)}
          />
        </label>
        <label className="field">
          Invoice reference
          <input
            required={!draft}
            value={invoice.reference}
            maxLength={60}
            onChange={(e) => update('reference', e.target.value)}
          />
        </label>
        <label className="field">
          Invoice date
          <input
            required={!draft}
            type="date"
            value={invoice.date}
            onChange={(e) => update('date', e.target.value)}
          />
        </label>
        <label className="field">
          Supplier WhatsApp (optional)
          <input
            placeholder="e.g. 919876543210"
            value={invoice.supplier_phone}
            pattern="\+?[0-9]{0,15}"
            maxLength={16}
            onChange={(e) => update('supplier_phone', e.target.value)}
          />
        </label>
      </div>
      <div className="line-items">
        {invoice.lines.map((l, i) => (
          <div className="line-editor" key={i}>
            <div className="line-top">
              <label className="field grow">
                Item {i + 1}
                <input
                  required={!draft}
                  aria-label={`Item ${i + 1} name`}
                  maxLength={120}
                  value={l.name}
                  onChange={(e) => lineChange(i, 'name', e.target.value)}
                />
              </label>
              {invoice.lines.length > 1 && (
                <button
                  type="button"
                  className="icon-button remove-line"
                  aria-label={`Remove item ${i + 1}`}
                  onClick={() =>
                    update(
                      'lines',
                      invoice.lines.filter((_, n) => n !== i),
                    )
                  }
                >
                  <X size={16} />
                </button>
              )}
            </div>
            <div className="line-form-grid">
              <label className="field">
                Billed quantity
                <input
                  type="number"
                  required={!draft}
                  min="0.000001"
                  max="100000"
                  step="0.000001"
                  aria-label={`Item ${i + 1} billed quantity`}
                  value={l.billed}
                  onChange={(e) => lineChange(i, 'billed', e.target.value)}
                />
              </label>
              <label className="field">
                Billed unit
                <select
                  aria-label={`Item ${i + 1} billed unit`}
                  value={l.unit}
                  onChange={(e) => lineChange(i, 'unit', e.target.value)}
                >
                  {['unknown', 'pack', 'piece', 'carton', 'kg'].map((v) => (
                    <option key={v} value={v}>
                      {v}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                Net price / unit (₹)
                <input
                  type="number"
                  required={!draft}
                  min="0.01"
                  max="1000000"
                  step="0.01"
                  aria-label={`Item ${i + 1} unit price`}
                  value={l.price_paise ? l.price_paise / 100 : ''}
                  onChange={(e) => lineChange(i, 'price_paise', paiseFromInput(e.target.value))}
                />
              </label>
              {review && (
                <>
                  <label className="field received-field">
                    Actually received
                    <input
                      type="number"
                      required={!draft}
                      min="0"
                      max="100000"
                      step="0.000001"
                      aria-label={`Item ${i + 1} received quantity`}
                      value={l.received ?? ''}
                      placeholder="Count"
                      onChange={(e) =>
                        lineChange(i, 'received', e.target.value === '' ? null : e.target.value)
                      }
                    />
                  </label>
                  <label className="field">
                    Received unit
                    <select
                      aria-label={`Item ${i + 1} received unit`}
                      value={l.received_unit}
                      onChange={(e) => lineChange(i, 'received_unit', e.target.value)}
                    >
                      {['unknown', 'pack', 'piece', 'carton', 'kg'].map((v) => (
                        <option key={v} value={v}>
                          {v}
                        </option>
                      ))}
                    </select>
                  </label>
                </>
              )}
            </div>
            {review && (
              <label className="check-field">
                <input
                  type="checkbox"
                  checked={l.unit_confirmed}
                  onChange={(e) => lineChange(i, 'unit_confirmed', e.target.checked)}
                />
                I checked that billed and received units match.
              </label>
            )}
            {l.note && (
              <p className="item-note">
                <AlertCircle size={14} />
                {l.note}
              </p>
            )}
          </div>
        ))}
      </div>
      <button
        type="button"
        className="text-button add-line"
        disabled={invoice.lines.length >= 30}
        onClick={() => update('lines', [...invoice.lines, freshLine()])}
      >
        <Plus size={15} /> Add an item
      </button>
    </>
  );
}

export { InvoiceModal, InvoiceFields };
