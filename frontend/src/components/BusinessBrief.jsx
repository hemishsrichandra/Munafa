import React, { useState, useEffect } from 'react';
import { api, money } from '../api';
import { useSession } from '../session';
export function BusinessBrief({ follow }) {
  const [data, setData] = useState(null),
    [error, setError] = useState('');
  async function load() {
    setError('');
    try {
      setData(await api('/brief'));
    } catch (e) {
      setError(e.message);
    }
  }
  useEffect(() => {
    load();
    const refresh = () => load();
    window.addEventListener('online', refresh);
    window.addEventListener('munafa-server-change', refresh);
    return () => {
      window.removeEventListener('online', refresh);
      window.removeEventListener('munafa-server-change', refresh);
    };
  }, []);
  return (
    <section className="panel partner-screen brief-screen" aria-label="Evidence-backed daily brief">
      <header className="brief-heading">
        <h2>Needs your attention</h2>
        <small>{data?.payment_label || 'Checking connected data…'}</small>
      </header>
      {error && (
        <div role="alert" className="error-box">
          {error}
          <button onClick={load}>Retry brief</button>
        </div>
      )}
      {!data && !error && <p role="status">Loading brief…</p>}
      {data && (
        <>
          <small>
            Updated{' '}
            {new Date(data.generated_at).toLocaleTimeString('en-IN', {
              hour: 'numeric',
              minute: '2-digit',
            })}
          </small>
          <details className="brief-payments">
            <summary>Yesterday’s payments</summary>
            <p>
              Yesterday’s recorded collections:{' '}
              {data.yesterday.recorded_collections_paise === null
                ? 'Unavailable'
                : money(data.yesterday.recorded_collections_paise)}{' '}
              · Recorded settlements:{' '}
              {data.yesterday.recorded_settlements_paise === null
                ? 'Unavailable'
                : money(data.yesterday.recorded_settlements_paise)}
            </p>
            <small>{data.yesterday.coverage}</small>
          </details>
          {!data.items.length && (
            <p>
              You’re all caught up. Add a purchase to start tracking your stock and supplier claims.
            </p>
          )}
          <div className="commerce-list">
            {data.items.map((item) => (
              <article className="panel" key={item.action_id}>
                <small>
                  {item.mode === 'demo' ? 'SYNTHETIC DEMO · ' : ''}
                  {item.data_freshness.stale
                    ? 'Older records · check for updates'
                    : 'Ready to review'}
                </small>
                <h3>{item.title}</h3>
                <p>
                  {item.type === 'reconciliation'
                    ? 'Check the settlement breakdown against the recorded payout.'
                    : item.reason}
                </p>
                {item.type === 'reconciliation' && (
                  <details>
                    <summary>Why this needs review</summary>
                    <p>{item.reason}</p>
                  </details>
                )}
                <small>
                  Record updated {new Date(item.data_freshness.source_updated_at).toLocaleString()}
                </small>
                <button className="button secondary" onClick={() => follow(item.route)}>
                  Review source
                </button>
              </article>
            ))}
          </div>
          {data.omitted_count > 0 && (
            <p>
              {data.omitted_count} additional source actions. Open the relevant workspace to review
              all.
            </p>
          )}
        </>
      )}
    </section>
  );
}
export function Payments({ initialId = '' }) {
  const session = useSession();
  const [data, setData] = useState(null),
    [error, setError] = useState(''),
    [busy, setBusy] = useState(false);
  async function load() {
    setError('');
    try {
      let result = await api(`/payments?mode=${session.store.demo ? 'demo' : 'live'}`);
      if (initialId) result = await api('/payments?mode=demo');
      setData(result);
    } catch (e) {
      setError(e.message);
    }
  }
  useEffect(() => {
    load();
  }, []);
  async function demo() {
    setBusy(true);
    setError('');
    try {
      setData(await api('/payments/demo', { method: 'POST' }));
      window.dispatchEvent(new Event('munafa-server-change'));
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="panel partner-screen">
      <h1>Payments & reconciliation</h1>
      <p>
        Review recorded settlements and any differences. Paytm is not connected; bank receipt is not
        verified.
      </p>
      <div className="commerce-tabs">
        <button className="button secondary" onClick={load} disabled={busy}>
          Check connection status
        </button>
        {session.store.demo && session.permissions.includes('admin') && (
          <button className="button secondary" onClick={demo} disabled={busy}>
            {busy ? 'Loading…' : 'Load sample settlements'}
          </button>
        )}
      </div>
      {error && (
        <p role="alert" className="error-box">
          {error}
        </p>
      )}
      {!data && !error && <p role="status">Loading payment status…</p>}
      {data && (
        <>
          <h2>{data.label}</h2>
          <p>Checked {new Date(data.updated_at).toLocaleString()}</p>
          {!data.settlements.length && (
            <p>No payment records yet. Connect Paytm to review your settlements here.</p>
          )}
          {data.settlements
            .filter((r) => !initialId || r.batch_id === initialId)
            .map((r) => (
              <article className="panel" key={r.batch_id}>
                <strong>
                  {r.mode === 'demo' ? 'SYNTHETIC DEMO · ' : ''}
                  {r.source_id}
                </strong>
                <p>
                  {r.status} · {r.stale ? 'Stale observation' : 'Recent observation'} ·{' '}
                  {new Date(r.observed_at).toLocaleString()}
                </p>
                <dl>
                  {Object.entries(r.components_paise).map(([k, v]) => (
                    <div key={k}>
                      <dt>
                        {{
                          gross: 'Collections',
                          commission: 'Fees',
                          gst: 'GST on fees',
                          refund: 'Refunds',
                          reversal: 'Reversals',
                          adjustment: 'Adjustments',
                        }[k] || k}
                      </dt>
                      <dd>
                        {r.missing_fields.some((f) => f.endsWith(':' + k + '_paise'))
                          ? 'Incomplete'
                          : money(v)}
                      </dd>
                    </div>
                  ))}
                </dl>
                <p>
                  Expected net:{' '}
                  {r.expected_net_paise === null
                    ? 'Cannot calculate: missing fields'
                    : money(r.expected_net_paise)}{' '}
                  · Recorded payout:{' '}
                  {r.recorded_settled_paise === null
                    ? 'Unavailable'
                    : money(r.recorded_settled_paise)}
                </p>
                <p>
                  Difference requiring review:{' '}
                  {r.difference_paise === null ? 'Unknown' : money(r.difference_paise)}
                </p>
                <ul>
                  {r.reasons.map((x) => (
                    <li key={x.code}>{x.detail}</li>
                  ))}
                </ul>
              </article>
            ))}
        </>
      )}
    </section>
  );
}
