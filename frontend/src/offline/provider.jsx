import React, { createContext, useContext, useEffect, useState, useRef } from 'react';
import { api } from '../api';
import * as db from './db';
import { syncBatch } from './sync';
const Offline = createContext(null);
export const useOffline = () => useContext(Offline);
export function OfflineProvider({ session, onAuthProblem, children }) {
  const scope = db.scopeOf(session);
  const [snapshot, setSnapshot] = useState({
    drafts: [],
    operations: [],
    cache: null,
    status: null,
  });
  const [error, setError] = useState('');
  const [ready, setReady] = useState(false);
  const [online, setOnline] = useState(navigator.onLine);
  const [busy, setBusy] = useState(false);
  const running = useRef(false),
    controller = useRef(null),
    stopped = useRef(false);
  const refresh = async () => {
    try {
      if ((await db.context())?.scope !== scope) {
        onAuthProblem?.(0);
        return;
      }
      const [drafts, operations, caches, status] = await Promise.all(
        ['drafts', 'outbox', 'cache', 'status'].map((s) => db.list(s, scope)),
      );
      const cache = caches.find((c) => Array.isArray(c.cases) && c.expires_at > Date.now()) || null;
      setSnapshot({ drafts, operations, cache, status: status[0] });
      setReady(true);
    } catch (e) {
      setError(db.storageMessage(e));
    }
  };
  const sync = async () => {
    if (
      running.current ||
      stopped.current ||
      !navigator.onLine ||
      session.offlineAccess ||
      session.offlineUnavailable
    )
      return;
    running.current = true;
    setBusy(true);
    controller.current = new AbortController();
    try {
      const attempted = await syncBatch({ scope, api, signal: controller.current.signal });
      if (attempted) window.dispatchEvent(new Event('munafa-server-change'));
    } catch (e) {
      if ([401, 403].includes(e.status))
        onAuthProblem?.((await db.context())?.scope !== scope ? 0 : e.status);
      else setError(db.storageMessage(e));
    } finally {
      running.current = false;
      setBusy(false);
      await refresh();
    }
  };
  useEffect(() => {
    stopped.current = false;
    if (session.offlineUnavailable) {
      setError(session.offlineUnavailable);
      setReady(true);
      return;
    }
    db.cleanup(scope)
      .then(refresh)
      .catch((e) => setError(db.storageMessage(e)));
    const unsubscribe = db.subscribe(refresh);
    const resume = () => {
      setOnline(navigator.onLine);
      if (document.visibilityState !== 'hidden') {
        if (!navigator.onLine)
          db.context().then((c) => {
            if (c?.expires_at < Date.now()) onAuthProblem?.(401);
          });
        else sync();
      }
    };
    const stop = () => {
      stopped.current = true;
      controller.current?.abort();
    };
    window.addEventListener('online', resume);
    window.addEventListener('offline', resume);
    window.addEventListener('munafa-stop-sync', stop);
    document.addEventListener('visibilitychange', resume);
    const timer = setInterval(resume, 15000);
    sync();
    return () => {
      stop();
      unsubscribe();
      clearInterval(timer);
      window.removeEventListener('online', resume);
      window.removeEventListener('offline', resume);
      window.removeEventListener('munafa-stop-sync', stop);
      document.removeEventListener('visibilitychange', resume);
    };
  }, [scope, session.offlineAccess]);
  return (
    <Offline.Provider
      value={{ ...snapshot, scope, error, setError, online, busy, ready, refresh, sync }}
    >
      {children}
    </Offline.Provider>
  );
}
