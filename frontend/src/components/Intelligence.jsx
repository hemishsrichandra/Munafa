import React, { useState } from 'react';
import { api } from '../api';

export function Intelligence() {
  const [data, setData] = useState(null),
    [busy, setBusy] = useState(false),
    [error, setError] = useState('');
  async function load() {
    setBusy(true);
    setError('');
    try {
      setData(await api('/intelligence/readiness'));
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="panel">
      <h2>Data readiness & evaluation</h2>
      <p>
        No forecast or peer benchmark is enabled. Payment totals and billed invoice quantities are
        not SKU sales.
      </p>
      <button className="button secondary" disabled={busy} onClick={load}>
        Check recorded SKU data
      </button>
      {busy && <p role="status">Checking recorded sources…</p>}
      {error && (
        <p className="error-box" role="alert">
          {error}
        </p>
      )}
      {data && (
        <>
          <p>
            {data.mode === 'demo' ? 'DEMO DATA · ' : ''}
            {data.coverage} · Queried {new Date(data.queried_at).toLocaleString()}. Refresh requires
            connection; this is a snapshot.
          </p>
          {!data.products.length && (
            <p>
              No SKU records yet. Create a product and record actual physical receiving; sales
              require separate evidence.
            </p>
          )}
          {data.products.map((p) => (
            <article className="panel" key={p.product_id}>
              <h3>
                {p.name} · {p.unit}
              </h3>
              <p>
                <strong>{p.status}</strong>
              </p>
              <p>
                {p.event_counts.sale || 0} accepted sale events on{' '}
                {p.observed_sales_period.distinct_days} observed days. Unrecorded days are unknown,
                not zero sales.
              </p>
              <p>
                Merchant reorder threshold: {p.simple_rule.threshold ?? 'Not set'} {p.unit}. This is
                a simple rule, not a forecast.
              </p>
              <ul>
                {p.reasons.map((r) => (
                  <li key={r}>{r}</li>
                ))}
              </ul>
            </article>
          ))}
          <p>Peer comparison suppressed: {data.benchmark.reason}</p>
          <p>{data.pilot.status} · Measured merchant outcomes not available.</p>
        </>
      )}
    </section>
  );
}
