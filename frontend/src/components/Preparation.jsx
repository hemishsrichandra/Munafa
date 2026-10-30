import React, { useState } from 'react';
import { api, downloadPrivate, money, today } from '../api';

export function Preparation() {
  const [start, setStart] = useState(today());
  const [end, setEnd] = useState(today());
  const [pack, setPack] = useState(null);
  const [proposal, setProposal] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [downloadUrl, setDownloadUrl] = useState('');
  async function downloadPack(url) {
    await downloadPrivate(url, 'unreviewed-preparation.json');
    setDownloadUrl('');
    setMessage('Downloaded to your device. Nothing was submitted.');
  }
  async function run(work) {
    setBusy(true);
    setError('');
    setMessage('');
    try {
      await work();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  function changed(update, value) {
    update(value);
    setPack(null);
    setProposal(null);
    setMessage('');
  }
  return (
    <section className="panel">
      <h2>Export purchases</h2>
      <p>
        Download confirmed purchases for your accountant. This is not a tax return; professional
        review is still needed.
      </p>
      <label className="field">
        Period start
        <input
          type="date"
          value={start}
          disabled={busy}
          onChange={(e) => changed(setStart, e.target.value)}
        />
      </label>
      <label className="field">
        Period end
        <input
          type="date"
          value={end}
          disabled={busy}
          onChange={(e) => changed(setEnd, e.target.value)}
        />
      </label>
      <button
        className="button secondary"
        disabled={busy || !start || !end}
        onClick={() =>
          run(async () => {
            setPack(null);
            setProposal(null);
            setPack(await api('/preparation/preview', { method: 'POST', body: { start, end } }));
          })
        }
      >
        Review purchases
      </button>
      {busy && <p role="status">Loading purchases…</p>}
      {error && (
        <p role="alert" className="error-box">
          {error}
        </p>
      )}
      {message && <p role="status">{message}</p>}
      {downloadUrl && (
        <button
          className="button secondary"
          disabled={busy}
          onClick={() => run(() => downloadPack(downloadUrl))}
        >
          Retry approved download
        </button>
      )}
      {pack && (
        <>
          <p>
            <strong>{pack.mode === 'demo' ? 'DEMO DATA · ' : ''}Accountant review needed</strong> ·{' '}
            {pack.records.length} confirmed purchases · {money(pack.total_recorded_paise)}
          </p>
          <small>Only confirmed purchases in this period are included.</small>
          {!pack.records.length && (
            <p>
              No confirmed purchases in this period. Accept a reviewed purchase or choose another
              period.
            </p>
          )}
          {pack.records.map((r) => (
            <article className="panel" key={r.purchase_id}>
              <h3>
                {r.supplier} · {r.reference}
              </h3>
              <p>
                {r.date} · {money(r.total_paise)} · {r.documents.length} source documents
              </p>
              {r.exceptions.length > 0 && (
                <small>
                  Tax details need your accountant’s review.
                  {!r.documents.length && ' No original bill is attached.'}
                </small>
              )}
            </article>
          ))}
          {!!pack.records.length && !proposal && (
            <button
              className="button secondary"
              disabled={busy}
              onClick={() =>
                run(async () => {
                  setProposal(
                    await api('/preparation/proposals', {
                      method: 'POST',
                      body: { start, end, source_ids: pack.records.map((r) => r.purchase_id) },
                    }),
                  );
                })
              }
            >
              Review download
            </button>
          )}
        </>
      )}
      {proposal && (
        <div className="panel">
          <h3>Confirm download</h3>
          <details>
            <summary className="button secondary">View included purchases</summary>
            <p>
              {proposal.payload.period.start} to {proposal.payload.period.end}
            </p>
            {proposal.payload.records.map((r) => (
              <article key={r.purchase_id}>
                <h4>
                  {r.supplier} · {r.reference}
                </h4>
                <p>
                  {r.date} · {money(r.total_paise)}
                </p>
                <p>
                  Recorded tax:{' '}
                  {r.tax_paise_recorded === null ? 'Not recorded' : money(r.tax_paise_recorded)}
                </p>
                <small>{r.documents.length} attached bills · Accountant review needed</small>
              </article>
            ))}
          </details>
          <p>
            {proposal.payload.records.length} purchases ·{' '}
            {money(proposal.payload.total_recorded_paise)}
          </p>
          <p>
            The file is saved to your device. Nothing is sent to an accountant or tax authority.
            Confirm within 15 minutes.
          </p>
          <button
            className="button primary"
            disabled={busy}
            onClick={() =>
              run(async () => {
                const approved = await api(`/actions/${proposal.id}/approve`, {
                  method: 'POST',
                  body: { version: proposal.version, payload_digest: proposal.payload_digest },
                });
                const result = await api(`/actions/${approved.id}/execute`, {
                  method: 'POST',
                  body: { version: approved.version },
                });
                setProposal(null);
                setDownloadUrl(result.download_url);
                await downloadPack(result.download_url);
              })
            }
          >
            Confirm and download
          </button>
        </div>
      )}
    </section>
  );
}
