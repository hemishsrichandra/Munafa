import React, { useEffect, useState } from 'react';
import { api } from './api';
const screens = ['My business', 'Updates for me', 'My actions', 'Ask with sources'];
export default function App() {
  const [user, setUser] = useState(null),
    [loading, setLoading] = useState(true),
    [error, setError] = useState('');
  const [username, setUsername] = useState(''),
    [password, setPassword] = useState(''),
    [view, setView] = useState(screens[0]);
  const [online, setOnline] = useState(navigator.onLine),
    [update, setUpdate] = useState(null);
  useEffect(() => {
    api('/auth/me')
      .then(setUser)
      .catch((e) => {
        if (e.status !== 401) setError(e.message);
      })
      .finally(() => setLoading(false));
    const connection = () => setOnline(navigator.onLine);
    window.addEventListener('online', connection);
    window.addEventListener('offline', connection);
    if (import.meta.env.PROD && 'serviceWorker' in navigator)
      navigator.serviceWorker
        .register('/sw.js')
        .then((reg) => {
          if (reg.waiting) setUpdate(reg.waiting);
          reg.addEventListener('updatefound', () => {
            const worker = reg.installing;
            worker?.addEventListener('statechange', () => {
              if (worker.state === 'installed' && navigator.serviceWorker.controller)
                setUpdate(worker);
            });
          });
        })
        .catch(() =>
          setError('Offline installation is unavailable. Online use is still available.'),
        );
    return () => {
      window.removeEventListener('online', connection);
      window.removeEventListener('offline', connection);
    };
  }, []);
  return (
    <main>
      <header>
        <strong>Regulatory Workspace</strong>
        {user && (
          <button
            onClick={async () => {
              setLoading(true);
              setError('');
              try {
                await api('/auth/logout', { method: 'POST' });
                setUser(null);
                setPassword('');
              } catch (e) {
                setError(e.message);
              } finally {
                setLoading(false);
              }
            }}
          >
            Sign out
          </button>
        )}
      </header>
      {!online && (
        <p className="notice" role="status">
          Offline. Live rules and account records cannot be checked. No legal advice is available
          from this starter.
        </p>
      )}
      {update && (
        <p className="notice">
          An app update is available. Finish any sign-in entry before reloading.{' '}
          <button
            onClick={() => {
              update.postMessage({ type: 'ACTIVATE_UPDATE' });
              navigator.serviceWorker.addEventListener(
                'controllerchange',
                () => location.reload(),
                { once: true },
              );
            }}
          >
            Reload app
          </button>
        </p>
      )}
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {loading ? (
        <p role="status">Loading workspace…</p>
      ) : !user ? (
        <section>
          <h1>Sign in</h1>
          <p>Your business account, kept separate from other businesses.</p>
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              setLoading(true);
              setError('');
              try {
                const result = await api('/auth/login', {
                  method: 'POST',
                  body: { username, password },
                });
                setUser(result);
                setPassword('');
              } catch (err) {
                setError(err.message);
              } finally {
                setLoading(false);
              }
            }}
          >
            <label>
              Username
              <input
                required
                autoComplete="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
              />
            </label>
            <label>
              Password
              <input
                required
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </label>
            <button className="primary" disabled={!online}>
              Sign in
            </button>
          </form>
          <small>
            Create your own account with the documented local command. No public sample account
            exists.
          </small>
        </section>
      ) : (
        <>
          <h1>{user.store.name}</h1>
          <nav aria-label="Workspace">
            {screens.map((s) => (
              <button
                key={s}
                aria-current={s === view ? 'page' : undefined}
                onClick={() => setView(s)}
              >
                {s}
              </button>
            ))}
          </nav>
          <section>
            <h2>{view}</h2>
            <p>
              This package contains the inherited application foundation. The regulatory workflow
              has not been built yet.
            </p>
            <p>
              No official sources are connected. No profile, legal determination, alert, deadline or
              AI answer has been generated.
            </p>
          </section>
        </>
      )}
      <footer>
        <small>Foundation starter · not a completed hackathon submission</small>
      </footer>
    </main>
  );
}
