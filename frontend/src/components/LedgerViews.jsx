import React, { useState, useEffect, useRef } from 'react';
import { ChartNoAxesCombined, ChevronRight, Download } from 'lucide-react';
import { money, exportLedger, downloadPrivate } from '../api';
import { useSession } from '../session';
import { badge } from './ui';
import { SupplierPerformance } from './SupplierPerformance';

function Suppliers({ cases, open }) {
  const groups = Object.values(
    cases.reduce((acc, c) => {
      const key = c.invoice.supplier.toLowerCase();
      acc[key] ||= { name: c.invoice.supplier, cases: [], owed: 0, recovered: 0 };
      acc[key].cases.push(c);
      if (c.approved_version) acc[key].owed += c.remaining_paise;
      acc[key].recovered += c.recovered_paise;
      return acc;
    }, {}),
  );
  return (
    <>
      <SupplierPerformance cases={cases} open={open} />
      <div className="supplier-grid">
        {groups.map((s) => (
          <section className="panel supplier-card" key={s.name}>
            <span className="supplier-logo">
              {s.name
                .split(' ')
                .slice(0, 2)
                .map((v) => v[0])
                .join('')}
            </span>
            <h2>{s.name}</h2>
            <p>
              {s.cases.length} invoice{s.cases.length !== 1 ? 's' : ''} tracked
            </p>
            <div className="supplier-totals">
              <div>
                <span>To resolve</span>
                <strong>{money(s.owed)}</strong>
              </div>
              <div>
                <span>Verified</span>
                <strong className="green-text">{money(s.recovered)}</strong>
              </div>
            </div>
            {s.cases.map((c) => (
              <button className="supplier-case" key={c.id} onClick={() => open(c)}>
                <span>{c.invoice.reference}</span>
                {badge(c.status)}
                <ChevronRight size={15} />
              </button>
            ))}
          </section>
        ))}
        {!groups.length && <p className="muted">Add an invoice to start your supplier ledger.</p>}
      </div>
    </>
  );
}
function Insights({ cases, verified, outstanding }) {
  const [exporting, setExporting] = useState(false),
    [exportError, setExportError] = useState('');
  const session = useSession();
  const approved = cases.filter((c) => c.approved_version !== null),
    closed = cases.filter((c) => c.status === 'resolved').length;
  const total = verified + outstanding,
    percentage = total ? Math.round((verified / total) * 100) : 0;
  return (
    <div className="insights-layout">
      <section className="panel insights-panel">
        <div className="panel-heading">
          <div>
            <h2>Reviewed value, tracked to resolution</h2>
            <p>Verified recovery as a share of all approved claim value.</p>
          </div>
          <button
            className="button secondary small"
            disabled={exporting || !session.permissions.includes('export')}
            onClick={async () => {
              if (!window.confirm('Approve export of the current store’s private supplier ledger?'))
                return;
              setExporting(true);
              setExportError('');
              try {
                const result = await exportLedger();
                await downloadPrivate(result.download_url, 'supplier-ledger.csv');
              } catch (e) {
                setExportError(e.message);
              } finally {
                setExporting(false);
              }
            }}
          >
            <Download size={15} />
            {exporting ? 'Preparing approved export…' : 'Export CSV'}
          </button>
        </div>
        {exportError && (
          <p className="error-box" role="alert">
            {exportError}
          </p>
        )}
        <div className="recovery-visual">
          <div
            className="recovery-ring"
            style={{
              background: `conic-gradient(#315b3e 0% ${percentage}%, #e9ede3 ${percentage}% 100%)`,
            }}
          >
            <div>
              <strong>{percentage}%</strong>
              <span>value verified</span>
            </div>
          </div>
          <div className="recovery-legend">
            <p>
              <i className="legend-green" />
              Verified credits and refunds <strong>{money(verified)}</strong>
            </p>
            <p>
              <i />
              Approved, still open <strong>{money(outstanding)}</strong>
            </p>
            <span>Drafts are excluded until the merchant approves them.</span>
          </div>
        </div>
        <div className="insight-summary">
          <div>
            <strong>
              {closed}/{approved.length}
            </strong>
            <span>Approved cases resolved</span>
          </div>
          <div>
            <strong>{cases.reduce((n, c) => n + c.resolutions.length, 0)}</strong>
            <span>Documented resolution records</span>
          </div>
        </div>
      </section>
      <section className="panel insights-note">
        <span className="section-icon">
          <ChartNoAxesCombined size={24} />
        </span>
        <h2>What’s included</h2>
        <p>
          Recovery totals include confirmed credits and received refunds. Open claims and supplier
          promises are shown separately.
        </p>
      </section>
    </div>
  );
}

export { Suppliers, Insights };
