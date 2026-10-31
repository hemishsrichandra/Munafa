import React, { useState } from 'react';
import { Modal } from './ui';

export function safeWhatsAppUrl(value) {
  try {
    const url = new URL(value);
    return url.protocol === 'https:' && url.hostname === 'wa.me' && !url.username && !url.password
      ? url.href
      : undefined;
  } catch {
    return undefined;
  }
}

export function ReviewedMessage({ title, text, original, url, close, promotional = false }) {
  const [reviewed, setReviewed] = useState(false);
  const link = safeWhatsAppUrl(url);
  return (
    <Modal title={title} subtitle="Review the message before opening WhatsApp" close={close}>
      <div className="modal-body">
        <div className="message-preview">{text}</div>
        {original && original !== text && (
          <>
            <h3>Original message</h3>
            <div className="message-preview">{original}</div>
          </>
        )}
        <p>
          WhatsApp opens a draft. You choose the recipient and send it yourself; this does not
          confirm delivery or payment.
        </p>
        <label className="check-field">
          <input
            type="checkbox"
            checked={reviewed}
            onChange={(e) => setReviewed(e.target.checked)}
          />
          {promotional
            ? 'I checked the batch, price and message, and will share only with customers who agreed to receive offers.'
            : 'I checked the customer, amount and message and have permission to contact them.'}
        </label>
        {!link && (
          <p role="status">
            No valid WhatsApp destination is available. Close this message and update the contact
            details.
          </p>
        )}
        <a
          role="link"
          className="button primary full"
          href={reviewed ? link : undefined}
          aria-disabled={!reviewed || !link}
          target="_blank"
          rel="noopener noreferrer"
        >
          Open WhatsApp
        </a>
      </div>
    </Modal>
  );
}
