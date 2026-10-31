import React, { useEffect, useState } from 'react';
import { api, isNative } from '../api';

export function AccountSecurity() {
  const [status, setStatus] = useState(null);
  const [policy, setPolicy] = useState(null);
  const [password, setPassword] = useState('');
  const [issued, setIssued] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [offline, setOffline] = useState(!navigator.onLine);
  async function load() {
    try {
      setStatus(await api('/auth/security'));
      setError('');
    } catch (e) {
      setError(e.message);
    }
  }
  useEffect(() => {
    load();
    const update = () => {
      setOffline(!navigator.onLine);
      if (navigator.onLine) load();
    };
    window.addEventListener('online', update);
    window.addEventListener('offline', update);
    return () => {
      window.removeEventListener('online', update);
      window.removeEventListener('offline', update);
    };
  }, []);
  async function generate(e) {
    e.preventDefault();
    if (
      status?.remaining_codes &&
      !window.confirm('Replace your old recovery codes? They will stop working immediately.')
    )
      return;
    setBusy(true);
    setError('');
    setIssued(null);
    try {
      setIssued(await api('/auth/recovery-codes', { method: 'POST', body: { password } }));
      setPassword('');
      await load();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  function download() {
    const text = `Munafa account recovery\nUsername: ${issued.username}\nExpires: ${issued.expires_at}\n\n${issued.codes.join('\n')}\n\nKeep these private, separate from this device. Use one code to reset your password. A reset revokes all codes and sessions; create a fresh set after signing in.\n`;
    const url = URL.createObjectURL(new Blob([text], { type: 'text/plain' }));
    const a = document.createElement('a');
    a.href = url;
    a.download = 'munafa-private-recovery-codes.txt';
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  return (
    <section className="panel account-security" aria-label="Account recovery" aria-busy={busy}>
      <h2>Account recovery</h2>
      {offline && (
        <p role="status">
          Reconnect to manage recovery codes. Codes are never saved in device drafts.
        </p>
      )}
      {error && (
        <p className="error-box" role="alert">
          {error}
          <button className="button secondary" disabled={offline || busy} onClick={load}>
            Retry account security
          </button>
        </p>
      )}
      {!status && !error && <p role="status">Loading account security…</p>}
      {status && !status.recovery_available && (
        <p>
          Create your own merchant account to set up recovery. Public demo accounts cannot be
          recovered.
        </p>
      )}
      {status?.recovery_available && (
        <>
          <p>
            {status.remaining_codes
              ? `${status.remaining_codes} unused recovery codes are available.`
              : 'No recovery codes saved yet. Set them up before you lose access.'}
          </p>
          <p className="tiny-help">
            Recovery uses a private code you save now. Email recovery is not connected. Codes expire
            after one year; a password reset revokes all codes and sessions.
          </p>
          <form onSubmit={generate}>
            <label className="field">
              Current password
              <input
                type="password"
                required
                maxLength={200}
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={offline || busy}
              />
            </label>
            <button className="button secondary" disabled={offline || busy}>
              {busy
                ? 'Preparing codes…'
                : status.remaining_codes
                  ? 'Replace recovery codes'
                  : 'Create recovery codes'}
            </button>
          </form>
        </>
      )}
      <details
        onToggle={(e) => {
          if (e.currentTarget.open && !policy && navigator.onLine)
            api('/auth/privacy')
              .then(setPolicy)
              .catch((e) => setError(e.message));
        }}
      >
        <summary>How your data is kept</summary>
        {!policy ? (
          <p>Connect to read the current storage and retention policy.</p>
        ) : (
          <>
            <p>{policy.private_device_cache}</p>
            <p>{policy.business_evidence}</p>
            <p>{policy.recovery_codes}</p>
            <p>{policy.cloud_ai}</p>
          </>
        )}
      </details>
      {issued && (
        <section className="recovery-code-sheet" aria-label="Save your recovery codes">
          <h3>Save these codes privately</h3>
          <p>
            Username: {issued.username}. This is the only time these codes are shown. Keep a copy
            somewhere you can access if this device is lost.
          </p>
          <ul>
            {issued.codes.map((code) => (
              <li key={code}>
                <code>{code}</code>
              </li>
            ))}
          </ul>
          {!isNative() && (
            <button className="button primary" onClick={download}>
              Download recovery codes
            </button>
          )}
          {isNative() && (
            <p>
              Select and save the codes privately. Native file export of recovery secrets has not
              been enabled.
            </p>
          )}
          <button className="button secondary" onClick={() => setIssued(null)}>
            I saved these codes
          </button>
        </section>
      )}
    </section>
  );
}
