import React, { useEffect, useState } from 'react';
import { api } from '../api';

export function Integrations() {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
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
    <section className="panel">
      <h2>Connections & readiness</h2>
      <p>No live provider is connected. Public documentation does not establish account access.</p>
      {!online && (
        <p role="status">Offline. Any displayed status is from this visit; reconnect to refresh.</p>
      )}
      {busy && <p role="status">Checking connection readiness…</p>}
      {error && (
        <p className="error-box" role="alert">
          {error}
        </p>
      )}
      <button className="button secondary" disabled={busy || !online} onClick={load}>
        Refresh status
      </button>
      {data && (
        <>
          <p>
            Checked {new Date(data.checked_at).toLocaleString()} · Store mode: {data.mode}
          </p>
          {data.capabilities.map((c) => (
            <article className="panel" key={c.id}>
              <h3>{c.label}</h3>
              <p>
                <strong>{c.status}</strong>
              </p>
              <p>Not connected · No successful sync · No external execution</p>
              <ul>
                {c.missing.map((reason) => (
                  <li key={reason}>{reason}</li>
                ))}
              </ul>
            </article>
          ))}
          {data.available_paths.map((p) => (
            <p key={p.label}>
              {p.label}: {p.status}
            </p>
          ))}
        </>
      )}
    </section>
  );
}
