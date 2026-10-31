import React, { useEffect, useState } from 'react';
import { api, money } from '../api';
import { useSession } from '../session';
import { ReviewedMessage } from './ReviewedMessage';

export function ExpiryRadar({ lots = [], asOf, stale = false, compact = false, follow }) {
  const session = useSession();
  const [offer, setOffer] = useState(null);
  const urgent = lots.filter((l) => l.urgency === 'critical' || l.expired);
  const visible = compact ? urgent : lots;
  const priced = visible.filter(
    (l) => Number.isSafeInteger(l.loss_risk_paise) && l.loss_risk_paise >= 0,
  );
  const total = priced.reduce((sum, l) => sum + BigInt(l.loss_risk_paise), 0n);
  const totalNumber = total <= BigInt(Number.MAX_SAFE_INTEGER) ? Number(total) : null;
  if (compact && !visible.length) return null;
  return (
    <section
      className="panel expiry-radar"
      aria-label={compact ? 'Expiry attention' : 'Expiry radar'}
    >
      <h2>{compact ? 'Check stock expiring this week' : 'Expiry radar'}</h2>
      <p>
        {lots.filter((l) => l.urgency === 'critical' && !l.expired).length} batches due within 7
        days · {lots.filter((l) => l.urgency === 'warning').length} due in 8–15 days ·{' '}
        {lots.filter((l) => l.expired).length} expired
      </p>
      <p>
        <strong>
          {priced.length && totalNumber !== null ? money(totalNumber) : 'Cost unavailable'}
        </strong>{' '}
        · estimated purchase cost at risk
        {priced.length < visible.length ? ' (some batch costs unavailable)' : ''}
      </p>
      <small>
        Based on the latest recorded purchase cost, not verified resale value or a confirmed loss.{' '}
        {asOf ? `Checked ${asOf}.` : 'Check dates before acting.'}{' '}
        {session.store.demo ? 'Synthetic demo data.' : ''}
      </small>
      {stale && (
        <p role="status">
          Saved information — reconnect to refresh stock and dates. Sharing is unavailable offline.
        </p>
      )}
      {compact ? (
        <button className="button secondary" onClick={() => follow('/stock/expiry')}>
          Open expiry radar
        </button>
      ) : (
        <>
          {!lots.length && (
            <p>
              No recorded batches expire within 30 days. Add batch dates when counting a delivery.
            </p>
          )}
          <div className="commerce-list">
            {visible.map((l) => (
              <article
                className={`expiry-card expiry-${l.urgency || (l.expired ? 'expired' : 'moderate')}`}
                key={l.id}
              >
                <h3>{l.product_name}</h3>
                <span className="badge">
                  {l.expired
                    ? 'Expired — remove from sale'
                    : l.days_until_expiry === 0
                      ? 'Expires today'
                      : Number.isInteger(l.days_until_expiry)
                        ? `Expires in ${l.days_until_expiry} days`
                        : 'Check expiry date'}
                </span>
                <p>
                  {l.quantity} {l.unit} · Batch {l.batch_reference || 'not recorded'} ·{' '}
                  {l.expiry_date}
                </p>
                <p>
                  Estimated purchase cost:{' '}
                  {Number.isSafeInteger(l.loss_risk_paise)
                    ? money(l.loss_risk_paise)
                    : 'Unavailable'}
                </p>
                {l.suggested_action && (
                  <p>
                    {l.expired ? 'Next step' : 'Suggested option — review first'}:{' '}
                    {l.suggested_action}
                  </p>
                )}
                {!l.expired && Number.isSafeInteger(l.suggested_clearance_price_paise) && (
                  <p>
                    Draft offer price: {money(l.suggested_clearance_price_paise)} per {l.unit} ·{' '}
                    {l.suggested_discount_percent}% below recorded purchase cost. Check your selling
                    price and margin.
                  </p>
                )}
                {!l.expired &&
                  session.permissions.includes('messaging') &&
                  l.whatsapp_liquidation_draft && (
                    <button
                      className="button secondary"
                      disabled={stale}
                      onClick={() => setOffer(l)}
                    >
                      Review clearance message
                    </button>
                  )}
                {!l.expired && !session.permissions.includes('messaging') && (
                  <small>
                    Your role can view stock; an authorised merchant can prepare messages.
                  </small>
                )}
              </article>
            ))}
          </div>
        </>
      )}
      {offer && (
        <ReviewedMessage
          title={`Clearance draft · ${offer.product_name}`}
          text={offer.whatsapp_liquidation_draft}
          url={`https://wa.me/?text=${encodeURIComponent(offer.whatsapp_liquidation_draft)}`}
          promotional
          close={() => setOffer(null)}
        />
      )}
    </section>
  );
}

export function ExpiryAttention({ follow }) {
  const [data, setData] = useState(null),
    [error, setError] = useState('');
  async function load() {
    setError('');
    if (!navigator.onLine) {
      setError('Reconnect to check batch expiry.');
      return;
    }
    try {
      setData(await api('/inventory/expiry'));
    } catch (e) {
      setError(e.message);
    }
  }
  useEffect(() => {
    load();
    const refresh = () => load();
    window.addEventListener('online', refresh);
    window.addEventListener('offline', refresh);
    window.addEventListener('munafa-server-change', refresh);
    return () => {
      window.removeEventListener('online', refresh);
      window.removeEventListener('offline', refresh);
      window.removeEventListener('munafa-server-change', refresh);
    };
  }, []);
  return (
    <>
      {!data && !error && <p role="status">Checking batch expiry…</p>}
      {error && (
        <p role="status">
          Expiry check unavailable: {error} <button onClick={load}>Retry expiry check</button>
        </p>
      )}
      {data && (
        <ExpiryRadar lots={data.lots} asOf={data.as_of} stale={!!error} compact follow={follow} />
      )}
    </>
  );
}
