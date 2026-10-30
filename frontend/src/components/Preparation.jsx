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
      <h2>Prepare records for review</h2>
      <p>
        Accepted purchase records only. Not CA-reviewed, a complete tax return, lender checklist or
        loan application. No external sharing occurs here.
      </p>
      <p>
        Connection required. Existing offline purchase drafts remain in Saved on this device; they
        are excluded until accepted by the server.
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
        Review accepted records
      </button>
      {busy && <p role="status">Preparing records…</p>}
      {error && (
        <p role="alert" className="error-box">
          {error}
        </p>
      )}
      {message && <p role="status">{message}</p>}
      {pack && (
        <>
          <p>
            <strong>{pack.mode === 'demo' ? 'DEMO DATA · ' : ''}Needs external review</strong> ·{' '}
            {pack.records.length} accepted purchases · {money(pack.total_recorded_paise)}
          </p>
          <p>{pack.coverage}</p>
          {!pack.records.length && (
            <p>
              No accepted purchases in this period. Accept a reviewed purchase or choose another
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
              {r.exceptions.map((e) => (
                <p key={e}>{e}</p>
              ))}
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
              Prepare local export for approval
            </button>
          )}
        </>
      )}
      {proposal && (
        <div className="panel">
          <h3>Review exact export</h3>
          <p>
            Recipient: your device only. Purpose: bookkeeping preparation.{' '}
            {proposal.payload.records.length} accepted source records;{' '}
            {money(proposal.payload.total_recorded_paise)}.
          </p>
          <p>
            No raw document bytes, customer contacts or provider credentials. Approval expires after
            15 minutes. This is not CA approval or submission.
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
                await downloadPrivate(
                  result.download_url.replace('/api', ''),
                  'unreviewed-preparation.json',
                );
                setProposal(null);
                setMessage(
                  'Preparation pack downloaded. It remains unreviewed; nothing was submitted.',
                );
              })
            }
          >
            Approve this local export and download
          </button>
        </div>
      )}
    </section>
  );
}
