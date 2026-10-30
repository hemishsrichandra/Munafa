import React, { createContext, useContext, useState, useEffect } from 'react';
import { api, clearNativeSession } from './api';
import * as local from './offline/db';
import { OfflineProvider } from './offline/provider';
const Session = createContext(null);
export const useSession = () => useContext(Session);
export function SessionGate({ children }) {
  const [demoAllowed, setDemoAllowed] = useState(false);
  const [session, setSession] = useState(null),
    [loading, setLoading] = useState(true),
    [error, setError] = useState('');
  const [username, setUsername] = useState(''),
    [password, setPassword] = useState(''),
    [demo, setDemo] = useState(false),
    [code, setCode] = useState('');
  const [offline, setOffline] = useState(!navigator.onLine);
  async function acceptSession(verified) {
    try {
      await local.activate(verified);
    } catch (e) {
      verified = { ...verified, offlineUnavailable: local.storageMessage(e) };
    }
    clearNativeCredentials(verified);
    setSession({ ...verified, offlineAccess: false });
  }
  function clearNativeCredentials(verified) {
    // Only identity/permissions go into IndexedDB; credentials remain in API memory/cookies.
    delete verified.session_token;
    delete verified.csrf;
  }
  async function restore() {
    let cached;
    try {
      cached = await local.context();
      if (await local.logoutPending()) {
        if (navigator.onLine) {
          try {
            await api('/auth/logout', { method: 'POST' });
            await local.clearPrivate(false);
          } catch (e) {
            if (e.status === 401) await local.clearPrivate(false);
          }
        }
        setSession(null);
        setError('Device signed out. Reconnect to finish server session revocation.');
        return;
      }
      try {
        await acceptSession(await api('/auth/me'));
      } catch (e) {
        if (!e.status && cached?.expires_at > Date.now() && cached.session?.user_id) {
          setSession({ ...cached.session, offlineAccess: true });
        } else {
          setSession(null);
          if (e.status === 403) await local.clearPrivate(false);
          if (e.status !== 401)
            setError(
              navigator.onLine
                ? e.message
                : 'Reconnect and sign in to unlock your saved workspace. Local drafts have been retained.',
            );
        }
      }
    } catch (e) {
      setError(local.storageMessage(e));
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    const refresh = () => {
      setOffline(!navigator.onLine);
      if (navigator.onLine) restore();
    };
    window.addEventListener('online', refresh);
    window.addEventListener('offline', refresh);
    api('/health')
      .then((cfg) => setDemoAllowed(cfg.development_login === true))
      .catch(() => {});
    restore();
    return () => {
      window.removeEventListener('online', refresh);
      window.removeEventListener('offline', refresh);
    };
  }, []);
  async function authProblem(status) {
    window.dispatchEvent(new Event('munafa-stop-sync'));
    if (status === 403) {
      await local.clearPrivate(false);
      setError(
        'Store access or membership changed. Previous private device data was cleared. Sign in again.',
      );
    } else if (status === 0) setError('Device workspace changed in another tab. Sign in again.');
    else
      setError(
        'Session expired. Your local drafts are retained. Sign in as the same merchant to resume.',
      );
    setSession(null);
  }
  async function logout() {
    if (
      !window.confirm(
        'Sign out and clear this device’s private drafts, attachments and cached records? Unsynced drafts will be removed.',
      )
    )
      return;
    window.dispatchEvent(new Event('munafa-stop-sync'));
    try {
      await local.clearPrivate(true);
      let revoked = false;
      if (navigator.onLine) {
        try {
          await api('/auth/logout', { method: 'POST' });
          revoked = true;
        } catch (e) {
          if (e.status === 401) revoked = true;
        }
      }
      clearNativeSession();
      if (revoked) await local.clearPrivate(false);
      setSession(null);
      setPassword('');
      setCode('');
      setError(
        revoked
          ? ''
          : 'Device data cleared. Server revocation requires connectivity; reconnect before sharing this device.',
      );
      navigator.serviceWorker?.controller?.postMessage({ type: 'PURGE_PRIVATE' });
    } catch (e) {
      setError(local.storageMessage(e));
    }
  }
  if (loading)
    return (
      <main className="login-page">
        <div className="skeleton" role="status">
          Loading your session…
        </div>
      </main>
    );
  if (!session)
    return (
      <main className="login-page">
        <section className="panel login-card">
          <div className="eyebrow">MUNAFA · KIRANA WORKSPACE</div>
          <h1>Paytm Business Partner</h1>
          <p>A clear picture of your supplier credits. No live Paytm connection.</p>
          {offline && (
            <div className="offline-banner" role="status">
              Reconnect to sign in. Previously verified workspaces can save local drafts offline for
              up to eight hours. Cloud AI requires connectivity.
            </div>
          )}
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              setLoading(true);
              setError('');
              try {
                await acceptSession(
                  await api(demo ? '/auth/dev-login' : '/auth/login', {
                    method: 'POST',
                    body: demo ? { code } : { username, password },
                  }),
                );
              } catch (e) {
                setError(e.message);
              } finally {
                setLoading(false);
              }
            }}
          >
            {demo ? (
              <label className="field">
                Private development access code
                <input
                  type="password"
                  required
                  minLength={16}
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  autoComplete="off"
                />
              </label>
            ) : (
              <>
                <label className="field">
                  Username
                  <input
                    required
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    autoComplete="username"
                  />
                </label>
                <label className="field">
                  Password
                  <input
                    required
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    autoComplete="current-password"
                  />
                </label>
              </>
            )}
            {error && (
              <p className="error-box" role="alert">
                {error}
              </p>
            )}
            <button className="button primary full" disabled={offline}>
              Sign in
            </button>
            {demoAllowed && (
              <button
                type="button"
                className="button secondary full"
                onClick={() => {
                  setDemo(!demo);
                  setError('');
                }}
              >
                {demo ? 'Use merchant account' : 'Development demo access'}
              </button>
            )}
          </form>
          <p className="tiny-help">
            Demo access works only when the server explicitly enables it. Get the private code from
            your local .env. Production disables it.
          </p>
        </section>
      </main>
    );
  return (
    <Session.Provider
      key={local.scopeOf(session)}
      value={{ ...session, logout, reconnect: restore }}
    >
      <OfflineProvider session={session} onAuthProblem={authProblem}>
        {children}
      </OfflineProvider>
    </Session.Provider>
  );
}
