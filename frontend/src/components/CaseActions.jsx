import React, { useState, useEffect, useRef } from 'react';
import {
  Check,
  ShieldCheck,
  Upload,
  FileText,
  Sparkles,
  Download,
  MessageCircle,
  Copy,
  CalendarDays,
  ExternalLink,
  LoaderCircle,
} from 'lucide-react';
import { api, money, day, today, downloadPrivate, paiseFromInput } from '../api';
import { icon, Modal, ErrorBox, Busy } from './ui';
import { safeWhatsAppUrl } from './ReviewedMessage';
import { saveEvidence } from '../evidence';

function Evidence({ c }) {
  const [error, setError] = useState('');
  return (
    <section className="evidence-card">
      <div className="evidence-top">
        <div className="evidence-brand">munafa.</div>
        <span>{c.synthetic ? 'SYNTHETIC EVIDENCE' : 'DELIVERY EVIDENCE'}</span>
      </div>
      <span className="evidence-caption">
        {c.approved_version ? 'MERCHANT-APPROVED CLAIM' : 'DRAFT · REQUIRES REVIEW'}
      </span>
      <strong className="evidence-total">
        {money(c.approved_amount_paise ?? c.calculation.amount_paise)}
      </strong>
      <h3>{c.invoice.supplier}</h3>
      <p>
        Invoice {c.invoice.reference} · {day(c.invoice.date)}
      </p>
      <div className="evidence-rule" />
      {c.invoice.lines.map((l, i) => (
        <div className="evidence-line" key={i}>
          <strong>{l.name}</strong>
          <div>
            <span>
              {l.billed} billed − {l.received ?? '?'} received
            </span>
            <b>{l.unit}</b>
          </div>
          {c.calculation.lines[i]?.issue ? (
            <span className="evidence-issue">Needs confirmation</span>
          ) : (
            <span className="equation">
              {c.calculation.lines[i]?.shortage_quantity} × {money(l.price_paise)} ={' '}
              {money(c.calculation.lines[i]?.amount_paise)}
            </span>
          )}
        </div>
      ))}
      <div className="evidence-rule" />
      <div className="evidence-trust">
        <ShieldCheck size={15} />
        {c.approved_version
          ? 'Counts and prices confirmed by merchant'
          : 'AI proposals need merchant confirmation'}
      </div>
      <ErrorBox text={error} />
      {c.approved_version && (
        <button
          className="button secondary full"
          onClick={async () => {
            setError('');
            try {
              await saveEvidence(c);
            } catch (e) {
              setError(e.message);
            }
          }}
        >
          <Download size={15} /> Download evidence card
        </button>
      )}
    </section>
  );
}
function ShareModal({ c, close, config, notify }) {
  const [lang, setLang] = useState('en-IN'),
    [draft, setDraft] = useState(null),
    [busy, setBusy] = useState(false),
    [error, setError] = useState('');
  const request = useRef(0);
  const [translationReviewed, setTranslationReviewed] = useState(false);
  async function generate(language) {
    const id = ++request.current;
    setLang(language);
    setDraft(null);
    setTranslationReviewed(false);
    setBusy(true);
    setError('');
    try {
      const res = await api(`/cases/${c.id}/message`, { method: 'POST', body: { language } });
      if (id === request.current) {
        setDraft(res);
        setLang(res.language || language);
      }
    } catch (e) {
      if (id === request.current) setError(e.message);
    } finally {
      if (id === request.current) setBusy(false);
    }
  }
  useEffect(() => {
    generate('en-IN');
    return () => {
      request.current++;
    };
  }, [c.id, c.version]);
  const link = safeWhatsAppUrl(draft?.whatsapp_url);
  const blocked =
    !translationReviewed || draft?.numeric_match === false || draft?.version !== c.version || !link;
  return (
    <Modal
      title="A message the supplier can act on."
      subtitle={`Invoice ${c.invoice.reference} · Review before you send`}
      close={close}
    >
      <div className="modal-body">
        <section className="claim-summary" aria-label="Approved claim amount">
          <small>Approved claim</small>
          <strong>{money(draft?.claim_amount_paise ?? c.approved_amount_paise)}</strong>
          {c.calculation.lines
            .filter((l) => l.amount_paise > 0)
            .map((l, i) => (
              <p key={i}>
                {l.shortage_quantity} missing · {money(l.amount_paise)}
              </p>
            ))}
        </section>
        <div className="language-pills" role="group" aria-label="Message language">
          {[
            ['en-IN', 'English'],
            ['hi-IN', 'हिन्दी'],
            ['kn-IN', 'ಕನ್ನಡ'],
          ].map(([code, label]) => (
            <button
              type="button"
              key={code}
              aria-pressed={lang === code}
              disabled={busy}
              onClick={() => generate(code)}
            >
              {label}
            </button>
          ))}
        </div>
        <ErrorBox text={error} />
        {error && (
          <button className="button secondary" disabled={busy} onClick={() => generate(lang)}>
            Retry message
          </button>
        )}
        {busy ? (
          <div className="loading">
            <LoaderCircle className="spin" size={20} /> Preparing message…
          </div>
        ) : (
          draft && (
            <>
              <div className="message-preview">{draft.text}</div>
              {lang !== 'en-IN' && (
                <>
                  <div className="info-box warm">
                    <Sparkles size={16} />
                    <p>
                      Check this translated draft: supplier, invoice reference, quantities and
                      amounts against the English original.
                    </p>
                  </div>
                  <section>
                    <h3>Original English message</h3>
                    <div className="message-preview">{draft.original}</div>
                  </section>
                </>
              )}
              <div className="info-box">
                <FileText size={17} />
                <p>
                  Download the evidence card, attach it in WhatsApp, then send. Come back to confirm
                  sharing.
                </p>
              </div>
              {draft && (
                <>
                  <label className="check-field">
                    <input
                      type="checkbox"
                      checked={translationReviewed}
                      onChange={(e) => setTranslationReviewed(e.target.checked)}
                    />
                    I reviewed the message against the approved claim, including amounts and
                    identifiers.
                  </label>
                  {draft.warning && <p role="alert">{draft.warning}</p>}
                </>
              )}
              <div className="action-row">
                <button
                  className="button secondary"
                  disabled={blocked}
                  onClick={async () => {
                    try {
                      await navigator.clipboard.writeText(draft.text);
                      notify('Supplier message copied.');
                    } catch {
                      setError(
                        'Copy is unavailable. Select the message text and copy it manually.',
                      );
                    }
                  }}
                >
                  <Copy size={16} /> Copy text
                </button>
                <button
                  className="button secondary"
                  onClick={async () => {
                    setError('');
                    try {
                      await saveEvidence(c);
                    } catch (e) {
                      setError(e.message);
                    }
                  }}
                >
                  <Download size={16} /> Evidence PNG
                </button>
                <a
                  role="link"
                  className="button primary"
                  aria-disabled={blocked}
                  href={blocked ? undefined : link}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  <MessageCircle size={16} /> Open WhatsApp
                </a>
              </div>
            </>
          )
        )}
      </div>
    </Modal>
  );
}
function PromiseModal({ c, close, update, notify }) {
  const [note, setNote] = useState(c.promise || ''),
    [date, setDate] = useState(c.follow_up && c.follow_up >= today() ? c.follow_up : today()),
    [busy, setBusy] = useState(false),
    [error, setError] = useState('');
  return (
    <Modal
      title="Record the supplier’s promise"
      subtitle="A promise helps you follow up. It does not count as recovery."
      close={close}
    >
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          setError('');
          try {
            update(
              await api(`/cases/${c.id}/promise`, {
                method: 'POST',
                body: { version: c.version, note, follow_up: date },
              }),
            );
            notify('Promise and follow-up date saved.');
            close();
          } catch (e) {
            setError(e.message);
          } finally {
            setBusy(false);
          }
        }}
      >
        <div className="modal-body">
          <label className="field">
            What did the supplier say?
            <textarea
              required
              maxLength={500}
              rows={3}
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Will adjust against the next bill."
            />
          </label>
          <label className="field">
            When should you follow up?
            <input
              required
              type="date"
              min={today()}
              value={date}
              onChange={(e) => setDate(e.target.value)}
            />
          </label>
          <ErrorBox text={error} />
          <button className="button primary full" disabled={busy}>
            <Busy busy={busy}>
              Save promise <CalendarDays size={16} />
            </Busy>
          </button>
        </div>
      </form>
    </Modal>
  );
}
function ResolveModal({ c, close, update, notify }) {
  const [data, setData] = useState({
      kind: 'credit',
      supplier: c.invoice.supplier,
      invoice_reference: c.invoice.reference,
      evidence_reference: '',
      amount_paise: c.remaining_paise,
      attachment_id: '',
      applied_confirmed: false,
    }),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(''),
    [proofName, setProofName] = useState('');
  const change = (key, value) =>
    setData((prev) => ({
      ...prev,
      [key]: value,
      ...(key === 'applied_confirmed' ? {} : { applied_confirmed: false }),
    }));
  async function sample() {
    setBusy(true);
    setError('');
    try {
      const p = await api(`/cases/${c.id}/sample-proof`, {
        method: 'POST',
        body: {
          amount_paise: data.amount_paise,
          kind: data.kind,
          evidence_reference: data.evidence_reference || null,
        },
      });
      const { synthetic, ...rest } = p;
      setData({ ...rest, applied_confirmed: false });
      setProofName('Synthetic next-bill credit');
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  async function upload(file) {
    if (!file) return;
    setBusy(true);
    setError('');
    try {
      const form = new FormData();
      form.append('file', file);
      const p = await api(`/cases/${c.id}/proof`, { method: 'POST', body: form });
      change('attachment_id', p.attachment_id);
      setProofName(p.name);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      update(
        await api(`/cases/${c.id}/resolve`, {
          method: 'POST',
          body: { ...data, version: c.version },
        }),
      );
      notify('Recovery verified and recorded once.');
      close();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <Modal
      title="Verify the money came back."
      subtitle={`${money(c.remaining_paise)} remains on invoice ${c.invoice.reference}`}
      close={close}
      closeDisabled={busy}
      wide
    >
      <form onSubmit={submit}>
        <div className="modal-body">
          <div className="info-box">
            <ShieldCheck size={18} />
            <p>
              Match the supplier, original invoice and amount against a credit note or refund
              record. Partial credits stay open. For a synthetic partial credit, enter the amount
              before loading its proof. A supplier promise alone is not proof.
            </p>
          </div>
          {c.synthetic && (
            <button
              type="button"
              className="button secondary full"
              disabled={busy}
              onClick={sample}
            >
              <Sparkles size={16} /> Load synthetic next-bill credit
            </button>
          )}
          <div className="form-grid resolution-form">
            <label className="field">
              How did the supplier pay?
              <select value={data.kind} onChange={(e) => change('kind', e.target.value)}>
                <option value="credit">Reduced from a bill</option>
                <option value="refund">Refund received</option>
              </select>
            </label>
            <label className="field">
              Money actually received or reduced from a bill (₹)
              <input
                required
                type="number"
                min="0.01"
                step="0.01"
                max={c.remaining_paise / 100}
                value={data.amount_paise / 100 || ''}
                onChange={(e) => change('amount_paise', paiseFromInput(e.target.value))}
              />
            </label>
            <label className="field">
              Supplier on the proof
              <input
                required
                maxLength={100}
                value={data.supplier}
                onChange={(e) => change('supplier', e.target.value)}
              />
            </label>
            <label className="field">
              Original invoice reference on proof
              <input
                required
                maxLength={60}
                value={data.invoice_reference}
                onChange={(e) => change('invoice_reference', e.target.value)}
              />
            </label>
            <label className="field span-two">
              Credit note or refund number
              <input
                required
                placeholder="e.g. CN-148 or bank transaction reference"
                maxLength={100}
                value={data.evidence_reference}
                onChange={(e) => change('evidence_reference', e.target.value)}
              />
            </label>
          </div>
          <label className="proof-upload">
            <Upload size={18} />
            <span>
              {proofName || 'Attach actual credit-note or refund proof'}
              <small>PNG, JPEG, WebP or PDF · up to 8 MB</small>
            </span>
            <input
              type="file"
              accept="image/png,image/jpeg,image/webp,application/pdf"
              disabled={busy}
              onChange={(e) => upload(e.target.files[0])}
            />
          </label>
          {data.attachment_id && (
            <a
              className="proof-link"
              href={`/api/attachments/${data.attachment_id}`}
              onClick={async (e) => {
                e.preventDefault();
                try {
                  await downloadPrivate(`/api/attachments/${data.attachment_id}`);
                } catch (e) {
                  setError(e.message);
                }
              }}
              target="_blank"
              rel="noreferrer"
            >
              <ExternalLink size={15} /> Open and inspect attached evidence
            </a>
          )}
          <label className="check-field resolution-check">
            <input
              type="checkbox"
              required
              disabled={busy || !data.attachment_id}
              checked={data.applied_confirmed}
              onChange={(e) => change('applied_confirmed', e.target.checked)}
            />
            I checked this proof and confirm the credit was applied or the refund was received.
          </label>
          <ErrorBox text={error} />
        </div>
        <div className="modal-footer">
          <span>Supplier + invoice + amount + proof</span>
          <button
            className="button primary"
            disabled={busy || !data.attachment_id || !data.applied_confirmed}
          >
            <Busy busy={busy}>
              <ShieldCheck size={16} /> Confirm money received
            </Busy>
          </button>
        </div>
      </form>
    </Modal>
  );
}

export { Evidence, ShareModal, PromiseModal, ResolveModal };
