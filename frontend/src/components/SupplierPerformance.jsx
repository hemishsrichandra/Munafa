import React, { useEffect, useState } from 'react';
import { api, money } from '../api';

export function SupplierPerformance({ cases, open }) {
  const [data, setData] = useState(null),
    [error, setError] = useState(''),
    [revision, setRevision] = useState(0);
  useEffect(() => {
    let active = true;
    const controller = new AbortController();
    setData(null);
    setError('');
    api('/supplier-performance', { signal: controller.signal })
      .then((v) => {
        if (active) setData(v);
      })
      .catch((e) => {
        if (active) setError(e.message);
      });
    return () => {
      active = false;
      controller.abort();
    };
  }, [cases, revision]);
  return (
    <section
      className="panel partner-screen daily-records"
      aria-label="Supplier performance summaries"
    >
      <h2>Documented supplier performance</h2>
      {error ? (
        <p role="status">
          {error}{' '}
          <button className="button secondary" onClick={() => setRevision((v) => v + 1)}>
            Retry supplier summaries
          </button>
        </p>
      ) : !data ? (
        <p role="status">Loading documented outcomes…</p>
      ) : (
        <>
          <p className="tiny-help">{data.coverage}</p>
          {!data.suppliers.length && <p>No tracked supplier cases yet.</p>}
          {data.suppliers.map((s) => (
            <details key={s.supplier}>
              <summary>
                {s.supplier} · {s.cases.filter((c) => c.approved && c.remaining_paise > 0).length}{' '}
                unresolved approved claims ·{' '}
                {money(s.cases.reduce((n, c) => n + (c.remaining_paise || 0), 0))} pending
              </summary>
              {s.cases.map((c) => (
                <article key={c.case_id}>
                  <h3>{c.reference}</h3>
                  <p>
                    {c.approved
                      ? `Approved claim · ${money(c.remaining_paise)} pending · ${money(c.recovered_paise)} recovered`
                      : 'Unapproved — excluded from approved shortage and pending totals'}
                  </p>
                  <p>
                    Approved missing / unusable quantities:{' '}
                    {c.shortages.length
                      ? c.shortages.map((l) => `${l.product}: ${l.quantity} ${l.unit}`).join('; ')
                      : 'None recorded'}
                  </p>
                  <p>
                    Damage on accepted receipts:{' '}
                    {c.damage.length
                      ? c.damage
                          .map((l) => `${l.quantity} ${l.unit} (receipt ${l.receipt_id})`)
                          .join('; ')
                      : 'No linked damage records; not proof of zero damage'}
                  </p>
                  <p>
                    Time to first recovery:{' '}
                    {c.first_recovery_hours === null
                      ? 'Not yet recorded'
                      : `${c.first_recovery_hours} hours`}
                    . Time to full recovery:{' '}
                    {c.full_recovery_hours === null
                      ? 'Not yet fully recovered'
                      : `${c.full_recovery_hours} hours`}
                    .
                  </p>
                  <button
                    className="button secondary"
                    onClick={() => {
                      const source = cases.find((x) => x.id === c.case_id);
                      if (source) open(source);
                    }}
                    disabled={!cases.some((x) => x.id === c.case_id)}
                  >
                    Open invoice and evidence {c.reference}
                  </button>
                </article>
              ))}
            </details>
          ))}
        </>
      )}
    </section>
  );
}
