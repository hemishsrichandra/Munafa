import React, { createContext, useContext, useState, useEffect } from 'react';
import { api, clearNativeSession } from './api';
import * as local from './offline/db';
import { OfflineProvider } from './offline/provider';
const Session = createContext(null);
export const useSession = () => useContext(Session);
export function SessionGate({ children }) {
  const [demoAllowed, setDemoAllowed] = useState(false);
  const [signupAllowed, setSignupAllowed] = useState(false);
  const [publicDemoAllowed, setPublicDemoAllowed] = useState(false);
  const [configError, setConfigError] = useState('');
  const [creatingAccount, setCreatingAccount] = useState(false);
  const [recovering, setRecovering] = useState(false);
  const [recoveryCode, setRecoveryCode] = useState('');
  const [authNotice, setAuthNotice] = useState('');
  const [storeName, setStoreName] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
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
    setPassword('');
    setConfirmPassword('');
    setCode('');
    setCreatingAccount(false);
    setRecovering(false);
    setRecoveryCode('');
    setAuthNotice('');
    setDemo(false);
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
    loadOptions();
    restore();
    return () => {
      window.removeEventListener('online', refresh);
      window.removeEventListener('offline', refresh);
    };
  }, []);
  async function loadOptions() {
    try {
      const cfg = await api('/health');
      setDemoAllowed(cfg.development_login === true);
      setSignupAllowed(cfg.public_signup === true);
      setPublicDemoAllowed(cfg.public_demo === true);
      setConfigError('');
    } catch {
      setConfigError('Account options could not load. Check your connection and retry.');
    }
  }
  function changeMode(signup = false, development = false, recovery = false) {
    setRecovering(recovery);
    setRecoveryCode('');
    setAuthNotice('');
    setCreatingAccount(signup);
    setDemo(development);
    setPassword('');
    setConfirmPassword('');
    setCode('');
    setError('');
  }
  async function startDemo() {
    setLoading(true);
    setError('');
    try {
      await acceptSession(await api('/auth/demo', { method: 'POST', body: {} }));
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }
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
          <p>
            {creatingAccount
              ? 'Create your private store workspace.'
              : 'Your purchases, stock and supplier credits in one place.'}
          </p>
          <h2>
            {recovering
              ? 'Recover account'
              : creatingAccount
                ? 'Create account'
                : demo
                  ? 'Development access'
                  : 'Welcome back'}
          </h2>
          {recovering && (
            <p>
              Use an unused recovery code you saved from your account. Email recovery is not
              available. If you have no code, contact your store administrator.
            </p>
          )}
          {authNotice && (
            <p className="info-box" role="status">
              {authNotice}
            </p>
          )}
          {offline && (
            <div className="offline-banner" role="status">
              Reconnect to sign in. Previously verified workspaces can save local drafts offline for
              up to eight hours. Cloud AI requires connectivity.
            </div>
          )}
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              if ((creatingAccount || recovering) && password !== confirmPassword) {
                setError('Passwords do not match. Please check both entries.');
                return;
              }
              setLoading(true);
              setError('');
              try {
                if (recovering) {
                  const result = await api('/auth/recover', {
                    method: 'POST',
                    body: { username, recovery_code: recoveryCode, new_password: password },
                  });
                  changeMode();
                  setAuthNotice(result.detail);
                  return;
                }
                await acceptSession(
                  await api(
                    creatingAccount ? '/auth/signup' : demo ? '/auth/dev-login' : '/auth/login',
                    {
                      method: 'POST',
                      body: creatingAccount
                        ? { username, password, store_name: storeName }
                        : demo
                          ? { code }
                          : { username, password },
                    },
                  ),
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
                Demo access code
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
                {creatingAccount && (
                  <label className="field">
                    Store name
                    <input
                      required
                      maxLength={120}
                      value={storeName}
                      onChange={(e) => setStoreName(e.target.value)}
                      autoComplete="organization"
                    />
                  </label>
                )}
                <label className="field">
                  Username
                  <input
                    required
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    autoComplete="username"
                    aria-describedby={creatingAccount ? 'signup-username-help' : undefined}
                    minLength={creatingAccount ? 3 : undefined}
                    maxLength={creatingAccount ? 60 : 120}
                    pattern={creatingAccount ? '[a-zA-Z0-9][a-zA-Z0-9._\\-]{2,59}' : undefined}
                    autoCapitalize="none"
                    spellCheck={false}
                  />
                </label>
                {creatingAccount && (
                  <p className="tiny-help" id="signup-username-help">
                    3–60 letters, numbers, dots, underscores or hyphens. Your username is saved in
                    lowercase.
                  </p>
                )}
                {recovering && (
                  <label className="field">
                    Recovery code
                    <input
                      required
                      value={recoveryCode}
                      maxLength={80}
                      autoComplete="off"
                      spellCheck={false}
                      autoCapitalize="characters"
                      onChange={(e) => setRecoveryCode(e.target.value)}
                    />
                  </label>
                )}
                <label className="field">
                  {recovering ? 'New password' : 'Password'}
                  <input
                    required
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    autoComplete={
                      creatingAccount || recovering ? 'new-password' : 'current-password'
                    }
                    minLength={creatingAccount || recovering ? 12 : undefined}
                    maxLength={200}
                  />
                </label>
                {(creatingAccount || recovering) && (
                  <>
                    <p className="tiny-help">
                      Use at least 12 characters. Set up and privately save your recovery codes from
                      Account recovery after signing in.
                    </p>
                    <label className="field">
                      Confirm password
                      <input
                        required
                        type="password"
                        minLength={12}
                        maxLength={200}
                        autoComplete="new-password"
                        value={confirmPassword}
                        onChange={(e) => setConfirmPassword(e.target.value)}
                      />
                    </label>
                  </>
                )}
              </>
            )}
            {error && (
              <p className="error-box" role="alert">
                {error}
              </p>
            )}
            <button className="button primary full" disabled={offline}>
              {recovering ? 'Reset password' : creatingAccount ? 'Create account' : 'Sign in'}
            </button>
            {creatingAccount || demo || recovering ? (
              <button type="button" className="button secondary full" onClick={() => changeMode()}>
                Back to sign in
              </button>
            ) : (
              <>
                <button
                  type="button"
                  className="button secondary full"
                  disabled={offline}
                  onClick={() => changeMode(false, false, true)}
                >
                  Recover account
                </button>
                {signupAllowed && (
                  <button
                    type="button"
                    className="button secondary full"
                    onClick={() => changeMode(true)}
                  >
                    Create account
                  </button>
                )}
                {publicDemoAllowed && (
                  <>
                    <button
                      type="button"
                      className="button secondary full"
                      disabled={offline}
                      onClick={startDemo}
                    >
                      Try a demo
                    </button>
                    <p className="tiny-help">
                      Explore a private demo with synthetic sample records. Use sample information
                      only. Signing out ends access; create an account for your own business.
                    </p>
                  </>
                )}
                {demoAllowed && (
                  <button
                    type="button"
                    className="button secondary full"
                    onClick={() => changeMode(false, true)}
                  >
                    Development demo access
                  </button>
                )}
              </>
            )}
          </form>
          {configError && (
            <div role="alert">
              <p>{configError}</p>
              <button
                type="button"
                className="button secondary"
                disabled={offline}
                onClick={loadOptions}
              >
                Retry account options
              </button>
            </div>
          )}
          <p className="tiny-help">
            No live Paytm connection. Ask your store administrator if you need help signing in.
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
