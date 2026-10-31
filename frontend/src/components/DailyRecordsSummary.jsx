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
        Sales are entries recorded for today. Customer udhaar and cash use your saved history. These
        are your entries, not a bank check or complete shop profit. Entries still on your phone are
        excluded.
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
              label="Today’s recorded sales · आज की बिक्री"
              value={money(summary.today.sales_paise)}
              Icon={ReceiptText}
              foot="Paid sales + sales on credit · View sources"
              onClick={() => openRecords(summary.source_routes.sales)}
            />
            <Metric
              label="Money to Collect · ग्राहक उधार"
              value={money(summary.customer_dues_paise)}
              Icon={Store}
              foot="Outstanding customer obligations · View sources"
              onClick={() => openRecords(summary.source_routes.dues)}
            />
            <Metric
              label="Cash in Galla · गल्ले में पैसा"
              value={
                summary.cash.opening_recorded
                  ? money(summary.cash.recorded_balance_paise)
                  : 'Not set'
              }
              Icon={Wallet}
              foot="Cash only · Count your galla"
              onClick={() => openRecords('/records/galla')}
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
