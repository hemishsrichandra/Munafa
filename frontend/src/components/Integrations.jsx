import React, { useEffect, useState } from 'react';
import { api } from '../api';

export function Integrations() {
  const [data, setData] = useState(null),
    [error, setError] = useState(''),
    [busy, setBusy] = useState(false);
  const [online, setOnline] = useState(navigator.onLine);
  async function load() {
    setBusy(true);
    setError('');
    try {
      setData(await api('/integrations/status'));
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  useEffect(() => {
    load();
    const update = () => setOnline(navigator.onLine);
    window.addEventListener('online', update);
    window.addEventListener('offline', update);
    return () => {
      window.removeEventListener('online', update);
      window.removeEventListener('offline', update);
    };
  }, []);
  return (
    <section className="panel partner-screen">
      <header>
        <div className="eyebrow">YOUR ACCOUNT</div>
        <h1>Connections</h1>
        <p>Manage how you get payment updates and share messages.</p>
      </header>
      {!online && (
        <p className="info-box" role="status">
          You’re offline. Reconnect to refresh connection status.
        </p>
      )}
      {error && (
        <p className="error-box" role="alert">
          {error}
        </p>
      )}
      {busy && <p role="status">Checking connections…</p>}
      {data && (
        <>
          <article>
            <h2>Paytm</h2>
            <span className="connection-status">Not connected</span>
            <p>Your Paytm payments aren’t connected to this store.</p>
            {data.mode === 'demo' && <small>Sample settlements are labelled as demo data.</small>}
          </article>
          <article>
            <h2>WhatsApp</h2>
            <span className="connection-status">Manual sharing</span>
            <p>
              Review a supplier message, then open WhatsApp to send it yourself. Delivery status
              isn’t tracked here.
            </p>
          </article>
          <small>Last checked {new Date(data.checked_at).toLocaleString()}</small>
        </>
      )}
      <button className="button secondary" disabled={busy || !online} onClick={load}>
        Refresh status
      </button>
    </section>
  );
}
