import React, { useEffect, useState } from 'react';
import { api } from '../api';

export function Intelligence({ follow }) {
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
  useEffect(() => {
    load();
  }, []);
  return (
    <section className="panel partner-screen">
      <header>
        <div className="eyebrow">PLAN YOUR STOCK</div>
        <h1>Stock planning</h1>
        <p>Your reorder levels, in one place.</p>
      </header>
      <p className="info-box">
        Forecasts need more reliable sales history. Reorder levels below are rules you set, not
        predictions.
      </p>
      {busy && <p role="status">Loading products…</p>}
      {error && (
        <p className="error-box" role="alert">
          {error}
        </p>
      )}
      {data && (
        <>
          {data.mode === 'demo' && <span className="demo-tag">Synthetic demo data</span>}
          {!data.products.length && (
            <p>No products yet. Add a product in Purchases & stock to set its reorder level.</p>
          )}
          {data.products.map((p) => (
            <article key={p.product_id}>
              <h2>
                {p.name} · {p.unit}
              </h2>
              <p>
                Reorder level:{' '}
                <strong>
                  {p.simple_rule.threshold === null
                    ? 'Not set'
                    : `${p.simple_rule.threshold} ${p.unit}`}
                </strong>
              </p>
              <small>Not enough sales history for a forecast.</small>
              <button className="button secondary" onClick={() => follow(p.route)}>
                Review {p.name} movement history
              </button>
            </article>
          ))}
          {data.truncated && (
            <p>Showing the first 100 products. Open Purchases & stock to see more.</p>
          )}
          <small>Updated {new Date(data.queried_at).toLocaleString()}. Reconnect to refresh.</small>
        </>
      )}
      <button className="button secondary" disabled={busy} onClick={load}>
        Refresh products
      </button>
    </section>
  );
}
