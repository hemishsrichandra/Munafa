import React, { useState, useEffect } from 'react';
import { api, money } from '../api';
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
    <section className="panel" aria-label="Evidence-backed daily brief">
      <h2>Your next recorded actions</h2>
      <p>{data?.payment_label || 'Checking connected data…'}</p>
      {error && (
        <div role="alert" className="error-box">
          {error}
          <button onClick={load}>Retry brief</button>
        </div>
      )}
      {!data && !error && <p role="status">Loading brief…</p>}
      {data && (
        <>
          <p>
            Updated {new Date(data.generated_at).toLocaleString()} · {data.timezone}
          </p>
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
          {!data.items.length && (
            <p>
              No evidence-backed actions are recorded. Add a purchase or set a SKU threshold to
              begin.
            </p>
          )}
          <div className="commerce-list">
            {data.items.map((item) => (
              <article className="panel" key={item.action_id}>
                <small>
                  {item.mode === 'demo' ? 'SYNTHETIC DEMO · ' : ''}
                  {item.status} ·{' '}
                  {item.data_freshness.stale ? 'Stale source · review freshness' : 'Source checked'}
                </small>
                <h3>{item.title}</h3>
                <p>{item.reason}</p>
                <small>
                  Source updated {new Date(item.data_freshness.source_updated_at).toLocaleString()}
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
  const [data, setData] = useState(null),
    [error, setError] = useState(''),
    [busy, setBusy] = useState(false);
  async function load() {
    setError('');
    try {
      let result = await api('/payments?mode=live');
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
    <section className="panel">
      <h1>Payments & reconciliation</h1>
      <p>
        Live Paytm access is disabled. Recorded statement fields explain differences; bank receipt
        is not verified.
      </p>
      <div className="commerce-tabs">
        <button className="button secondary" onClick={load} disabled={busy}>
          Check connection status
        </button>
        <button className="button secondary" onClick={demo} disabled={busy}>
          {busy ? 'Loading…' : 'Load isolated synthetic payment demo'}
        </button>
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
            <p>
              No connected payment records. Unavailable data is not zero activity. Demo loading
              requires a demo store and administrator permission.
            </p>
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
                      <dt>{k}</dt>
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
                <small>Linked source records: {r.source_entity_ids.join(', ')}</small>
              </article>
            ))}
        </>
      )}
    </section>
  );
}
