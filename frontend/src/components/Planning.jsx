import React, { useEffect, useState } from 'react';
import { api } from '../api';
import { useSession } from '../session';

const labels = {
  catalog_records: 'SKU records',
  supplier_records: 'Supplier records',
  accepted_purchases: 'Accepted purchases',
  accepted_physical_receipts: 'Accepted physical receipts',
  inventory_events: 'Accepted inventory events',
  live_settlement_observations: 'Live settlement observations',
  demo_settlement_observations: 'Synthetic settlement observations',
};
export function Planning({ follow }) {
  const session = useSession();
  const [data, setData] = useState(null),
    [error, setError] = useState(''),
    [busy, setBusy] = useState(false),
    [online, setOnline] = useState(navigator.onLine),
    [result, setResult] = useState(null),
    [selected, setSelected] = useState(''),
    [intent, setIntent] = useState({
      financial_planning: 'financial_summary',
      benchmarking: 'within_store_history',
    });
  async function load() {
    if (!navigator.onLine) {
      setOnline(false);
      return;
    }
    setBusy(true);
    setError('');
    try {
      setData(await api('/planning/readiness'));
      setResult(null);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  useEffect(() => {
    load();
    const refresh = () => {
      setOnline(navigator.onLine);
      if (navigator.onLine) load();
    };
    window.addEventListener('online', refresh);
    window.addEventListener('offline', refresh);
    window.addEventListener('munafa-server-change', refresh);
    return () => {
      window.removeEventListener('online', refresh);
      window.removeEventListener('offline', refresh);
      window.removeEventListener('munafa-server-change', refresh);
    };
  }, []);
  async function assess(capability) {
    setBusy(true);
    setError('');
    setResult(null);
    const source = data.source_samples.find((s) => s.id === selected);
    try {
      setResult(
        await api('/planning/assess', {
          method: 'POST',
          body: {
            capability,
            intent: capability === 'procurement' ? 'purchase_order_draft' : intent[capability],
            ...(capability === 'procurement' && source
              ? {
                  product: {
                    product_id: source.id,
                    expected_product_version: source.product_version,
                    expected_stock_version: source.stock_version,
                    unit: source.unit,
                    merchant_confirmed_need: false,
                  },
                }
              : {}),
          },
        }),
      );
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="panel partner-screen">
      <div>
        <div className="eyebrow">P2 · PREREQUISITES FIRST</div>
        <h1>Planning readiness</h1>
      </div>
      <p>
        Review what your recorded data can support. Ordering, lender submissions and peer
        comparisons are unavailable.
      </p>
      <button className="button secondary" onClick={load} disabled={busy || !online}>
        {busy ? 'Checking…' : 'Refresh readiness'}
      </button>
      {error && (
        <p role="alert" className="error-box">
          {error} Keep using your existing purchase and stock workflows.
        </p>
      )}
      {!online && (
        <p role="status">
          Offline · this snapshot may be stale. Reconnect to check current prerequisites; no
          planning action is queued.
        </p>
      )}
      {!data && !error && online && <p role="status">Loading store-scoped evidence…</p>}
      {!data && !online && (
        <p>
          No current readiness snapshot is available. Your saved drafts remain in Drafts &amp; sync.
        </p>
      )}
      {data && (
        <>
          <p>
            <strong>{data.label}</strong> · {online && !error ? 'Snapshot' : 'Stale snapshot'}{' '}
            checked {new Date(data.assessed_at).toLocaleString()}
          </p>
          <section>
            <h2>Recorded foundations</h2>
            <p>
              Record counts are not proof of completeness or data quality. Accepted invoices are not
              proof of unpaid debt; payment totals are not SKU sales.
            </p>
            <dl>
              {Object.entries(data.record_counts).map(([key, value]) => (
                <div key={key}>
                  <dt>{labels[key]}</dt>
                  <dd>{value}</dd>
                </div>
              ))}
            </dl>
          </section>
          {data.capabilities.map((cap) => {
            const permitted = session.permissions.includes(
              cap.id === 'financial_planning' ? 'admin' : 'write',
            );
            return (
              <article key={cap.id} aria-label={cap.label}>
                <h2>{cap.label}</h2>
                <strong>
                  {cap.status === 'disabled' ? 'Disabled' : 'Blocked'} · prerequisites unproven
                </strong>
                <small>
                  Risk: {cap.risk_classification.replaceAll('_', ' ')} · Feature flag{' '}
                  {cap.configuration.requested ? 'requested' : 'off'}
                </small>
                <p>{cap.uncertainty}</p>
                <details>
                  <summary>What blocks this capability?</summary>
                  <ul>
                    {cap.blockers.map((b) => (
                      <li key={b.code}>{b.detail}</li>
                    ))}
                  </ul>
                </details>
                {cap.id === 'procurement' && (
                  <label className="field">
                    Recorded SKU to inspect
                    <select
                      aria-label="Recorded SKU to inspect"
                      value={selected}
                      onChange={(e) => setSelected(e.target.value)}
                    >
                      <option value="">No SKU selected</option>
                      {data.source_samples.map((s) => (
                        <option key={s.id} value={s.id}>
                          {s.label} ({s.unit})
                        </option>
                      ))}
                    </select>
                  </label>
                )}
                {cap.id === 'financial_planning' && (
                  <label className="field">
                    Readiness purpose
                    <select
                      aria-label="Readiness purpose"
                      value={intent.financial_planning}
                      onChange={(e) => setIntent({ ...intent, financial_planning: e.target.value })}
                    >
                      <option value="financial_summary">Financial summary prerequisites</option>
                      <option value="lender_checklist">
                        Lender document-process prerequisites
                      </option>
                    </select>
                  </label>
                )}
                {cap.id === 'benchmarking' && (
                  <label className="field">
                    Comparison readiness
                    <select
                      aria-label="Comparison readiness"
                      value={intent.benchmarking}
                      onChange={(e) => setIntent({ ...intent, benchmarking: e.target.value })}
                    >
                      <option value="within_store_history">
                        Within-store history prerequisites
                      </option>
                      <option value="peer_comparison">Peer comparison prerequisites</option>
                    </select>
                  </label>
                )}
                <button
                  className="button secondary"
                  onClick={() => assess(cap.id)}
                  disabled={busy || !online || !permitted}
                >
                  Inspect {cap.id === 'financial_planning' ? 'financial' : cap.id} prerequisites
                </button>
                {!permitted && (
                  <p>
                    {cap.id === 'financial_planning'
                      ? 'Owner access is required for this financial readiness check.'
                      : 'Your role can read status; a write permission is required to record a readiness check.'}
                  </p>
                )}
              </article>
            );
          })}
          {result && (
            <section className="panel" aria-live="polite">
              <h2>Readiness check only</h2>
              <p>{result.notice}</p>
              <p>
                Checked {new Date(result.assessed_at).toLocaleString()} ·{' '}
                {result.mode === 'demo' ? 'Synthetic demo' : 'Your recorded store'} ·{' '}
                {result.capability.status}
              </p>
              <p>No proposal created · No external action performed · Consent not verified</p>
              <ul>
                {result.checks.map((c) => (
                  <li key={c.code}>{c.detail}</li>
                ))}
              </ul>
              {result.source_records.length > 0 && (
                <p>
                  {result.source_records.length} store-owned source record(s) inspected. A recorded
                  source is not a verified current supplier offer.
                </p>
              )}
            </section>
          )}
          <section>
            <h2>Your own recorded history</h2>
            <p>{data.safe_alternative}</p>
            <p>
              Peer results are suppressed. No cohort size, methodology or peer statistic is
              available.
            </p>
            {!data.source_samples.length && (
              <p>
                No SKU records yet. Add and physically receive products in Purchases &amp; stock to
                start a recorded timeline.
              </p>
            )}
            {data.source_samples_truncated && (
              <p>
                Showing up to {data.source_sample_limit} SKU examples. Open Purchases &amp; stock
                for your full catalogue.
              </p>
            )}
            {data.source_samples.map((s) => (
              <article key={s.id}>
                <h3>
                  {s.label} · {s.unit}
                </h3>
                <small>
                  {s.timestamp_basis} · {new Date(s.source_recorded_at).toLocaleString()}
                </small>
                <button
                  className="button secondary"
                  disabled={!online}
                  onClick={() => follow(s.route)}
                >
                  Review {s.label} movement history
                </button>
              </article>
            ))}
          </section>
        </>
      )}
    </section>
  );
}
