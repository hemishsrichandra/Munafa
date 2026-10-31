import React, { useState, useEffect, useRef } from 'react';
import { ReceiptText, ChevronRight, X, AlertCircle, LoaderCircle } from 'lucide-react';
import { money, day, today } from '../api';

const labels = {
  review: 'Check the bill',
  ready: 'Confirmed Shortage',
  sent: 'Waiting for supplier',
  promised: 'Supplier promised',
  partial: 'Some money returned',
  resolved: 'Money received',
};
const badge = (status) => (
  <span className={`badge ${status}`}>
    <i />
    {labels[status]}
  </span>
);
const icon = (Icon, size = 18) => <Icon size={size} strokeWidth={1.7} />;
function Metric({ label, value, Icon, foot, tone, onClick }) {
  const Element = onClick ? 'button' : 'div';
  return (
    <Element
      type={onClick ? 'button' : undefined}
      className={`metric ${onClick ? 'clickable' : ''}`}
      onClick={onClick}
    >
      <div className="metric-top">
        <span>{label}</span>
        <span className={`metric-icon ${tone}`}>{icon(Icon, 19)}</span>
      </div>
      <strong className="metric-value">{value}</strong>
      <span className="metric-foot">{foot}</span>
    </Element>
  );
}
function CaseTable({ cases, open }) {
  return (
    <>
      <div className="mobile-case-list">
        {cases.map((c) => (
          <button
            key={c.id}
            className="case-list-card"
            onClick={() => open(c)}
            aria-label={`Open invoice ${c.invoice.reference}`}
          >
            <span className="case-card-top">
              <strong>{c.invoice.supplier}</strong>
              {badge(c.status)}
            </span>
            <span className="case-card-reference">
              Invoice {c.invoice.reference} ·{' '}
              {c.synthetic ? 'Synthetic example' : day(c.invoice.date)}
            </span>
            <span className="case-card-bottom">
              <strong>
                {c.status === 'review' ? 'Needs your review' : money(c.remaining_paise)}
              </strong>
              <span>
                {c.follow_up ? `Follow up ${day(c.follow_up)}` : 'View case'}{' '}
                <ChevronRight size={18} />
              </span>
            </span>
          </button>
        ))}
      </div>
      <div className="table-scroll desktop-case-table">
        <table>
          <thead>
            <tr>
              <th>SUPPLIER / INVOICE</th>
              <th>TO RESOLVE</th>
              <th>STATUS</th>
              <th>FOLLOW-UP</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {cases.map((c) => (
              <tr
                key={c.id}
                onClick={() => open(c)}
                tabIndex={0}
                onKeyDown={(e) => e.key === 'Enter' && open(c)}
                aria-label={`Open invoice ${c.invoice.reference}`}
              >
                <td>
                  <div className="supplier-cell">
                    <span className={`supplier-logo ${c.status === 'resolved' ? 'mint' : ''}`}>
                      {c.invoice.supplier
                        .split(' ')
                        .slice(0, 2)
                        .map((s) => s[0])
                        .join('')}
                    </span>
                    <div>
                      <strong>{c.invoice.supplier}</strong>
                      <span>
                        {c.invoice.reference} <b>·</b>{' '}
                        {c.synthetic ? 'Synthetic example' : day(c.invoice.date)}
                      </span>
                    </div>
                  </div>
                </td>
                <td className="amount">
                  {c.status === 'review' ? (
                    <span className="muted">In review</span>
                  ) : (
                    money(c.remaining_paise)
                  )}
                  {c.status === 'resolved' && <small>{money(c.recovered_paise)} verified</small>}
                </td>
                <td>{badge(c.status)}</td>
                <td>
                  <span
                    className={
                      c.follow_up && c.follow_up < today() && c.status !== 'resolved'
                        ? 'overdue-date'
                        : 'table-date'
                    }
                  >
                    {c.follow_up && c.follow_up < today() && c.status !== 'resolved' ? (
                      <>
                        <i />
                        Overdue ·{' '}
                      </>
                    ) : null}
                    {day(c.follow_up)}
                  </span>
                </td>
                <td>
                  <ChevronRight size={17} className="muted" />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
function Empty({ onAdd }) {
  return (
    <div className="empty">
      <ReceiptText />
      <h3>Your next delivery starts here</h3>
      <p>Add a sample or your own invoice to check what arrived.</p>
      <button className="button primary" onClick={onAdd}>
        Add first invoice
      </button>
    </div>
  );
}
function Modal({ title, subtitle, close, children, wide = false, closeDisabled = false }) {
  const ref = useRef(null),
    oldFocus = useRef(document.activeElement);
  useEffect(() => {
    ref.current?.focus();
    const old = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = old;
      oldFocus.current?.focus();
    };
  }, []);
  const keys = (e) => {
    if (e.key === 'Escape' && !closeDisabled) close();
    if (e.key === 'Tab') {
      const els = [
        ...ref.current.querySelectorAll(
          'button:not(:disabled),input:not(:disabled),select:not(:disabled),textarea:not(:disabled),a[href],[tabindex="0"]',
        ),
      ];
      const first = els[0],
        last = els[els.length - 1];
      if (!els.length) {
        e.preventDefault();
        ref.current?.focus();
        return;
      }
      if (
        e.shiftKey &&
        (document.activeElement === first || document.activeElement === ref.current)
      ) {
        e.preventDefault();
        last?.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first?.focus();
      }
    }
  };
  return (
    <div
      className="modal-backdrop"
      onMouseDown={(e) => !closeDisabled && e.target === e.currentTarget && close()}
    >
      <section
        className={`modal ${wide ? 'wide' : ''}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby="dialog-title"
        ref={ref}
        tabIndex={-1}
        onKeyDown={keys}
      >
        <div className="modal-header">
          <div>
            <h2 id="dialog-title">{title}</h2>
            {subtitle && <p>{subtitle}</p>}
          </div>
          <button
            className="icon-button"
            onClick={close}
            aria-label="Close dialog"
            disabled={closeDisabled}
          >
            <X size={20} />
          </button>
        </div>
        {children}
      </section>
    </div>
  );
}
function ErrorBox({ text }) {
  return text ? (
    <div className="error-box" role="alert">
      <AlertCircle size={18} />
      <span>{text}</span>
    </div>
  ) : null;
}
function Busy({ busy, children }) {
  return (
    <>
      {busy ? <LoaderCircle size={17} className="spin" /> : null}
      {children}
    </>
  );
}

export { labels, badge, icon, Metric, CaseTable, Empty, Modal, ErrorBox, Busy };
