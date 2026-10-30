import { isNative } from './api';
import React, { useEffect, useState } from 'react';
export function PwaControls() {
  const [offline, setOffline] = useState(!navigator.onLine),
    [update, setUpdate] = useState(null),
    [prompt, setPrompt] = useState(null),
    [guidance, setGuidance] = useState(false);
  const [installed, setInstalled] = useState(
    isNative() || matchMedia('(display-mode: standalone)').matches || navigator.standalone === true,
  );
  useEffect(() => {
    const network = () => setOffline(!navigator.onLine),
      before = (e) => {
        e.preventDefault();
        setPrompt(e);
      },
      done = () => {
        setInstalled(true);
        setPrompt(null);
      };
    window.addEventListener('online', network);
    window.addEventListener('offline', network);
    window.addEventListener('beforeinstallprompt', before);
    window.addEventListener('appinstalled', done);
    let interval;
    if (import.meta.env.PROD && !isNative() && 'serviceWorker' in navigator) {
      navigator.serviceWorker
        .register('/sw.js', { scope: '/' })
        .then((reg) => {
          if (reg.waiting) setUpdate(reg.waiting);
          reg.addEventListener('updatefound', () => {
            const worker = reg.installing;
            worker?.addEventListener('statechange', () => {
              if (worker.state === 'installed' && navigator.serviceWorker.controller)
                setUpdate(worker);
            });
          });
          interval = setInterval(() => reg.update().catch(() => {}), 60000);
        })
        .catch(() => setGuidance(true));
    }
    return () => {
      window.removeEventListener('online', network);
      window.removeEventListener('offline', network);
      window.removeEventListener('beforeinstallprompt', before);
      window.removeEventListener('appinstalled', done);
      clearInterval(interval);
    };
  }, []);
  return (
    <div className="pwa-status">
      {offline && (
        <div className="offline-banner" role="status">
          Offline · use Drafts & sync for saved device work. Cloud AI and server approval require a
          connection. Queued operations are provisional.
        </div>
      )}
      {update && (
        <div className="update-banner" role="status">
          <span>An app update is ready. Finish or save your current work first.</span>
          <button
            onClick={() => {
              if (
                window.confirm(
                  'Reload to update? Unsaved form input will be lost. Cancel to finish your work.',
                )
              ) {
                navigator.serviceWorker.addEventListener(
                  'controllerchange',
                  () => location.reload(),
                  { once: true },
                );
                update.postMessage({ type: 'ACTIVATE_UPDATE' });
              }
            }}
          >
            Update when ready
          </button>
        </div>
      )}
      <div className="install-control">
        {installed ? (
          <span>Installed app</span>
        ) : (
          <button
            onClick={async () => {
              if (prompt) {
                await prompt.prompt();
                setPrompt(null);
              } else setGuidance(!guidance);
            }}
          >
            Install app
          </button>
        )}
        {guidance && !installed && (
          <div className="install-guide" role="status">
            Connect first and open the site once to cache the shell. In Chrome use “Install app”; in
            Safari use Share → Add to Home Screen. Installation support varies. Server records and
            AI require a connection. Device drafts are stored separately in IndexedDB.
          </div>
        )}
      </div>
    </div>
  );
}
