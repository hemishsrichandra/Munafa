import React, { useState, useEffect, useRef } from 'react';
import {
  ArrowUpRight,
  ArrowRight,
  ChevronRight,
  Check,
  CheckCheck,
  ShieldCheck,
  Clock3,
  FileText,
  ArrowLeft,
  MessageCircle,
  CalendarDays,
  AlertCircle,
  Mic,
  ExternalLink,
  Settings2,
} from 'lucide-react';
import { api, money, day, today, isNative, downloadPrivate } from '../api';
import { useSession } from '../session';
import { badge, icon, Modal, ErrorBox, Busy } from './ui';
import { InvoiceFields } from './InvoiceIntake';
import { Evidence, ShareModal, PromiseModal, ResolveModal } from './CaseActions';

function CaseDetail({ c, onUpdate, back, config, notify }) {
  const session = useSession();
  const [invoice, setInvoice] = useState(c.invoice),
    [complete, setComplete] = useState(c.delivery_complete),
    [pricing, setPricing] = useState(c.pricing_confirmed);
  const [editing, setEditing] = useState(false),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(''),
    [dialog, setDialog] = useState(null),
    [speech, setSpeech] = useState('');
  const recognitionRef = useRef(null);
  useEffect(() => {
    setInvoice(c.invoice);
    setComplete(c.delivery_complete);
    setPricing(c.pricing_confirmed);
  }, [c.version]);
  useEffect(() => () => recognitionRef.current?.abort(), []);
  const dirty =
    JSON.stringify(invoice) !== JSON.stringify(c.invoice) ||
    complete !== c.delivery_complete ||
    pricing !== c.pricing_confirmed;
  async function run(path, body = {}) {
    setBusy(true);
    setError('');
    try {
      const result = await api(`/cases/${c.id}/${path}`, {
        method: path === 'review' ? 'PATCH' : 'POST',
        body: { version: c.version, ...body },
      });
      onUpdate(result);
      setEditing(false);
      notify(
        path === 'review'
          ? 'Review saved. Check the evidence before approving.'
          : path === 'approve'
            ? 'Evidence approved. You can prepare a supplier message.'
            : 'Case updated.',
      );
      return true;
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  function voiceCount() {
    if (isNative()) {
      setSpeech('Voice is not enabled in this Android shell. Enter the received quantity below.');
      return;
    }
    const Speech = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!Speech) {
      setSpeech('Voice isn’t supported in this browser. Use the received-quantity fields below.');
      return;
    }
    recognitionRef.current?.abort();
    const rec = new Speech();
    recognitionRef.current = rec;
    rec.lang = 'en-IN';
    rec.interimResults = false;
    rec.onstart = () =>
      setSpeech('Listening… Say a count for the first item, for example “ten packs arrived”.');
    rec.onresult = (e) => {
      const text = e.results[0][0].transcript;
      const words = {
        zero: 0,
        one: 1,
        two: 2,
        three: 3,
        four: 4,
        five: 5,
        six: 6,
        seven: 7,
        eight: 8,
        nine: 9,
        ten: 10,
        eleven: 11,
        twelve: 12,
      };
      const matches =
        text
          .toLowerCase()
          .match(
            /\b(\d+|zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\b/g,
          ) || [];
      if (matches.length === 1) {
        const count = words[matches[0]] ?? Number(matches[0]);
        setInvoice((prev) => ({
          ...prev,
          lines: prev.lines.map((l, i) => (i === 0 ? { ...l, received: count } : l)),
        }));
        setSpeech(
          `Heard “${text}”. Proposed count for the first item: ${count}. Check the count and confirm the unit below.`,
        );
      } else setSpeech(`Heard “${text}”. Please enter a single clear count in the fields below.`);
    };
    rec.onerror = (e) => setSpeech(`Voice input unavailable (${e.error}). Enter the count below.`);
    try {
      rec.start();
    } catch {
      setSpeech('Could not start voice input. Use the quantity fields below.');
    }
  }
  const stage =
    c.status === 'review' ? 0 : c.status === 'ready' ? 1 : c.status === 'resolved' ? 3 : 2;
  return (
    <>
      <button className="text-button back-button" onClick={back}>
        <ArrowLeft size={16} /> Back to workspace
      </button>
      <div className="page-heading case-heading">
        <div>
          <div className="eyebrow">
            {c.id} {c.synthetic ? '· SYNTHETIC EXAMPLE' : '· MERCHANT INVOICE'}
          </div>
          <h1>Invoice {c.invoice.reference}</h1>
          <p>
            {c.invoice.supplier} <span className="dot-sep">·</span> {day(c.invoice.date)}{' '}
            <span className="dot-sep">·</span> {badge(c.status)}
          </p>
        </div>
        <div className="case-heading-actions">
          {c.attachment_id && (
            <a
              className="button secondary"
              href={`/api/attachments/${c.attachment_id}`}
              onClick={async (e) => {
                e.preventDefault();
                try {
                  await downloadPrivate(`/api/attachments/${c.attachment_id}`);
                } catch (e) {
                  setError(e.message);
                }
              }}
              target="_blank"
              rel="noreferrer"
            >
              <FileText size={16} /> Original bill
            </a>
          )}
          {c.status !== 'review' && !c.resolutions.length && !editing && (
            <button className="button secondary" onClick={() => setEditing(true)}>
              <Settings2 size={16} /> Edit inputs
            </button>
          )}
        </div>
      </div>
      <div className="steps">
        {['Confirm delivery', 'Approve evidence', 'Follow up', 'Verify resolution'].map((s, i) => (
          <div key={s} className={i <= stage ? 'current' : ''}>
            <span>{i < stage ? <Check size={14} /> : i + 1}</span>
            {s}
            {i < 3 && <ChevronRight size={15} />}
          </div>
        ))}
      </div>
      {!session.permissions.includes('approve') && (
        <div className="info-box" role="status">
          Your role can review records but cannot approve, share or record recovery. Ask the store
          owner.
        </div>
      )}
      <ErrorBox text={error} />
      <div className="detail-layout">
        <div className="detail-main">
          {c.status === 'review' || editing ? (
            <section className="panel review-panel">
              <div className="panel-heading">
                <div>
                  <h2>What actually arrived?</h2>
                  <p>Check the bill, count the goods, and confirm each unit.</p>
                </div>
                <button className="button subtle small" onClick={voiceCount}>
                  <Mic size={15} /> Try voice
                </button>
              </div>
              {speech && (
                <div className="info-box">
                  <Mic size={16} />
                  <p>{speech}</p>
                </div>
              )}
              {editing && (
                <div className="info-box warm">
                  <AlertCircle size={17} />
                  <p>
                    Saving changes invalidates the previous approval and follow-up. Review and share
                    the updated evidence again.
                  </p>
                </div>
              )}
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  run('review', {
                    invoice,
                    delivery_complete: complete,
                    pricing_confirmed: pricing,
                  });
                }}
              >
                <InvoiceFields invoice={invoice} change={setInvoice} review />
                <div className="confirmation-box">
                  <label className="check-field">
                    <input
                      type="checkbox"
                      checked={complete}
                      onChange={(e) => setComplete(e.target.checked)}
                    />
                    The delivery is complete. No remaining items are on the way.
                  </label>
                  <label className="check-field">
                    <input
                      type="checkbox"
                      checked={pricing}
                      onChange={(e) => setPricing(e.target.checked)}
                    />
                    I verified effective unit prices after any tax, discount or scheme.
                  </label>
                  <p>{invoice.pricing_note}</p>
                </div>
                <div className="review-actions">
                  <span className="muted">Changes are saved only when you choose.</span>
                  <button className="button primary" disabled={busy || !dirty}>
                    <Busy busy={busy}>
                      Save delivery review <Check size={16} />
                    </Busy>
                  </button>
                </div>
              </form>
            </section>
          ) : (
            <section className="panel">
              <div className="panel-heading">
                <div>
                  <h2>Confirmed delivery</h2>
                  <p>Merchant-reviewed counts and effective prices.</p>
                </div>
                <ShieldCheck size={21} className="green-text" />
              </div>
              <div className="confirmed-lines">
                {c.invoice.lines.map((l, i) => (
                  <div key={i}>
                    <span className="line-check">
                      <Check size={16} />
                    </span>
                    <div>
                      <strong>{l.name}</strong>
                      <span>
                        {l.billed} billed · {l.received} received · {l.unit}
                      </span>
                    </div>
                    <strong>
                      {l.billed - l.received
                        ? money(c.calculation.lines[i].amount_paise)
                        : 'Matched'}
                    </strong>
                  </div>
                ))}
              </div>
            </section>
          )}
          {c.status === 'ready' && !editing && (
            <section className="panel action-panel">
              <div className="section-icon">{icon(MessageCircle, 24)}</div>
              <h2>A clear request starts the conversation.</h2>
              <p>
                Preview the supplier message and attach your downloaded evidence card in WhatsApp.
                Return here after you send it.
              </p>
              <button className="button primary" onClick={() => setDialog('share')}>
                Prepare supplier message <ArrowRight size={16} />
              </button>
              <div className="sent-confirm">
                <label className="check-field">
                  <input
                    id="sent-check"
                    type="checkbox"
                    onChange={(e) => e.target.checked && setDialog('sent')}
                  />
                  I have sent the approved evidence to the supplier.
                </label>
              </div>
            </section>
          )}
          {['sent', 'promised', 'partial'].includes(c.status) && !editing && (
            <section className="panel action-panel">
              <div className="panel-heading">
                <div>
                  <h2>Keep the credit moving.</h2>
                  <p>A promise stays open until the adjustment or refund is verified.</p>
                </div>
                {icon(Clock3, 22)}
              </div>
              {c.promise && (
                <blockquote>
                  “{c.promise}”<span>Follow up {day(c.follow_up)}</span>
                </blockquote>
              )}
              <div className="action-row">
                <button className="button secondary" onClick={() => setDialog('promise')}>
                  <CalendarDays size={16} />
                  {c.promise ? 'Update follow-up' : 'Record supplier promise'}
                </button>
                <button className="button primary" onClick={() => setDialog('resolve')}>
                  <ShieldCheck size={16} /> Verify credit / refund
                </button>
                <button className="text-button" onClick={() => setDialog('share')}>
                  Supplier message <ArrowUpRight size={14} />
                </button>
              </div>
            </section>
          )}
          {c.status === 'resolved' && (
            <section className="resolution-success">
              <div className="success-icon">
                <CheckCheck size={27} />
              </div>
              <div>
                <h2>Every rupee, accounted for.</h2>
                <p>
                  {money(c.recovered_paise)} verified against documented evidence. This case is
                  resolved.
                </p>
              </div>
            </section>
          )}
          {!!c.resolutions.length && (
            <section className="panel">
              <div className="panel-heading">
                <div>
                  <h2>Recorded recovery</h2>
                  <p>Each evidence reference is counted once.</p>
                </div>
              </div>
              <div className="resolution-list">
                {c.resolutions.map((r) => (
                  <div key={r.id}>
                    <span className="proof-icon">
                      <ShieldCheck size={19} />
                    </span>
                    <div>
                      <strong>{r.kind === 'credit' ? 'Credit applied' : 'Refund received'}</strong>
                      <span>
                        {r.evidence_reference} · {day(r.at)}
                      </span>
                    </div>
                    <strong>{money(r.amount_paise)}</strong>
                    <a
                      href={`/api/attachments/${r.attachment_id}`}
                      onClick={async (e) => {
                        e.preventDefault();
                        try {
                          await downloadPrivate(`/api/attachments/${r.attachment_id}`);
                        } catch (e) {
                          setError(e.message);
                        }
                      }}
                      target="_blank"
                      rel="noreferrer"
                      aria-label={`View proof ${r.evidence_reference}`}
                    >
                      <ExternalLink size={16} />
                    </a>
                  </div>
                ))}
              </div>
            </section>
          )}
          <section className="panel">
            <div className="panel-heading">
              <div>
                <h2>The full paper trail</h2>
                <p>Every review, promise and verified resolution.</p>
              </div>
            </div>
            <ol className="timeline">
              {[...c.history].reverse().map((h, i) => (
                <li key={`${h.at}-${i}`}>
                  <span className="timeline-dot" />
                  <div>
                    <strong>{h.action}</strong>
                    <p>{h.detail}</p>
                    {h.snapshot && (
                      <a
                        className="snapshot-link"
                        href={`/api/cases/${c.id}/approvals/${h.snapshot.version}`}
                        target="_blank"
                        rel="noreferrer"
                      >
                        View approved snapshot <ExternalLink size={11} />
                      </a>
                    )}
                    <time>
                      {new Date(h.at).toLocaleString('en-IN', {
                        day: 'numeric',
                        month: 'short',
                        hour: 'numeric',
                        minute: '2-digit',
                        timeZone: 'Asia/Kolkata',
                      })}{' '}
                      IST
                    </time>
                  </div>
                </li>
              ))}
            </ol>
          </section>
        </div>
        <aside className="detail-aside">
          <Evidence c={c} />
          {c.status === 'review' && (
            <div className="approval-box">
              {c.calculation.issues.length ? (
                <>
                  <h3>
                    <AlertCircle size={17} /> A few things to confirm
                  </h3>
                  <ul>
                    {c.calculation.issues.map((issue, i) => (
                      <li key={i}>{issue}</li>
                    ))}
                  </ul>
                </>
              ) : (
                <p>
                  {c.calculation.amount_paise > 0
                    ? 'Review the saved counts and calculation above, then approve your evidence.'
                    : 'All quantities match. There is no delivery shortage to claim.'}
                </p>
              )}
              {dirty && <p className="unsaved">Save your latest changes before approving.</p>}
              <button
                className="button primary full"
                disabled={
                  busy ||
                  dirty ||
                  !c.calculation.eligible ||
                  !session.permissions.includes('approve')
                }
                onClick={() => run('approve')}
              >
                <Busy busy={busy}>
                  <ShieldCheck size={16} /> Approve evidence
                </Busy>
              </button>
            </div>
          )}
          {c.approved_version && (
            <div className="balance-card">
              <span>Still to verify</span>
              <strong>{money(c.remaining_paise)}</strong>
              <div>
                <span>Verified so far</span>
                <b>{money(c.recovered_paise)}</b>
              </div>
              <p>Only applied credits and received refunds count toward recovery.</p>
            </div>
          )}
          <div className="aside-note">
            <ShieldCheck size={18} />
            <p>
              AI helps read the bill. Your confirmations and deterministic rules establish the
              claim.
            </p>
          </div>
        </aside>
      </div>
      {dialog === 'share' && (
        <ShareModal c={c} close={() => setDialog(null)} config={config} notify={notify} />
      )}
      {dialog === 'sent' && (
        <Modal
          title="Confirm you sent the evidence"
          subtitle="Opening WhatsApp alone does not mark a case as sent."
          close={() => {
            setDialog(null);
            document.getElementById('sent-check').checked = false;
          }}
        >
          <div className="modal-body">
            <p>
              Confirm that you sent the approved message and attached the evidence for invoice{' '}
              {c.invoice.reference} to {c.invoice.supplier}.
            </p>
            <p className="muted">
              This is your record of sharing. Munafa cannot verify message delivery or read
              receipts.
            </p>
            <button
              className="button primary full"
              disabled={busy}
              onClick={async () => {
                if (await run('sent', { confirmed: true })) setDialog(null);
              }}
            >
              Yes, I sent the evidence <Check size={16} />
            </button>
          </div>
        </Modal>
      )}
      {dialog === 'promise' && (
        <PromiseModal c={c} close={() => setDialog(null)} update={onUpdate} notify={notify} />
      )}
      {dialog === 'resolve' && (
        <ResolveModal c={c} close={() => setDialog(null)} update={onUpdate} notify={notify} />
      )}
    </>
  );
}

export default CaseDetail;
