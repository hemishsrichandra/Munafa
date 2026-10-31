import React, { useEffect, useState } from 'react';
import { Wallet, ReceiptText, Clock3, Store } from 'lucide-react';
import { api, money } from '../api';
import { Metric } from './ui';

// Read existing server totals, never the last-100-entry history or provisional drafts.
export function DailyRecordsSummary({ openRecords }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    async function load() {
      setData(null);
      setError('');
      if (!navigator.onLine) {
        setError('Reconnect to load recorded business totals. Device drafts are not included.');
        return;
      }
      try {
        const brief = await api('/brief', { signal: controller.signal });
        if (active) setData(brief.manual_totals);
      } catch (e) {
        if (active) setError(e.message);
      }
    }
    load();
    const refresh = () => setRevision((v) => v + 1);
    window.addEventListener('online', refresh);
    window.addEventListener('offline', refresh);
    window.addEventListener('munafa-server-change', refresh);
    return () => {
      active = false;
      controller.abort();
      window.removeEventListener('online', refresh);
      window.removeEventListener('offline', refresh);
      window.removeEventListener('munafa-server-change', refresh);
    };
  }, [revision]);
  const summary = data;
  return (
    <section className="panel partner-screen daily-records" aria-label="Recorded business snapshot">
      <div className="brief-heading">
        <h2>Recorded business snapshot</h2>
        <button className="button secondary" onClick={() => openRecords('/records/customers')}>
          Open daily records
        </button>
      </div>
      <p className="tiny-help">
        Merchant-reviewed manual records · all recorded dates. Not total shop sales, profit or
        verified bank data. Unsynced device drafts are excluded.
      </p>
      {error ? (
        <div role="status">
          <p>{error}</p>
          <button className="button secondary" onClick={() => setRevision((v) => v + 1)}>
            Retry business snapshot
          </button>
        </div>
      ) : !data ? (
        <p role="status">Loading recorded business totals…</p>
      ) : (
        <>
          <p className="tiny-help">
            As of {summary.business_date}
            {summary.mode === 'demo' ? ' · Synthetic demo records' : ''}
          </p>
          <div className="metrics">
            <Metric
              label="Recorded sales"
              value={money(summary.sales_paise)}
              Icon={ReceiptText}
              foot="Paid sales + sales on credit · View sources"
              onClick={() => openRecords(summary.source_routes.sales)}
            />
            <Metric
              label="Customer dues"
              value={money(summary.customer_dues_paise)}
              Icon={Store}
              foot="Outstanding customer obligations · View sources"
              onClick={() => openRecords(summary.source_routes.dues)}
            />
            <Metric
              label="Recorded expenses"
              value={money(summary.expenses_paise)}
              Icon={Wallet}
              foot="All payment channels · View sources"
              onClick={() => openRecords(summary.source_routes.expenses)}
            />
            <Metric
              label="Open tasks"
              value={summary.open_tasks}
              Icon={Clock3}
              foot="Tasks visible to your account · View sources"
              onClick={() => openRecords(summary.source_routes.tasks)}
            />
          </div>
          <p className="tiny-help">
            Cash drawer:{' '}
            {summary.cash.opening_recorded
              ? money(summary.cash.recorded_balance_paise)
              : 'Unknown — record opening cash first'}
            . Cash movements only; bank/UPI entries do not change this amount.
          </p>
        </>
      )}
    </section>
  );
}
