import React, { useEffect, useRef, useState } from 'react';
import { api, isNative, money } from '../api';
import guide from '../../../backend/knowledge/product-v1.json';
export function CachedHelp() {
  return (
    <details className="panel">
      <summary>Offline help</summary>
      <p>Bundled implementation guidance. Account policies need current official support.</p>
      {guide.documents
        .filter((d) => d.kind === 'product_source')
        .map((d) => (
          <section key={d.id}>
            <h3>{d.section}</h3>
            <p>{d.text}</p>
            <small>Updated {d.reviewed_at}</small>
          </section>
        ))}
    </details>
  );
}
export function VoiceNote({ enabled, change }) {
  const [state, setState] = useState('idle'),
    [message, setMessage] = useState(''),
    [consent, setConsent] = useState(false),
    [language, setLanguage] = useState('en-IN');
  const recorder = useRef(null),
    stream = useRef(null),
    timer = useRef(null),
    active = useRef(true),
    discard = useRef(false);
  function release() {
    clearTimeout(timer.current);
    stream.current?.getTracks().forEach((t) => t.stop());
    stream.current = null;
  }
  function stop() {
    if (recorder.current?.state === 'recording') recorder.current.stop();
    release();
  }
  useEffect(() => {
    active.current = true;
    return () => {
      active.current = false;
      discard.current = true;
      stop();
    };
  }, []);
  async function start() {
    if (!enabled || !consent || !navigator.onLine || isNative()) {
      setMessage('Voice preview is unavailable here. Type your note instead.');
      return;
    }
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
      setMessage('Recording is unsupported in this browser. Type your note instead.');
      return;
    }
    discard.current = false;
    setMessage('Requesting microphone permission…');
    setState('requesting');
    try {
      const media = await navigator.mediaDevices.getUserMedia({ audio: true });
      if (!active.current || discard.current) {
        media.getTracks().forEach((t) => t.stop());
        return;
      }
      stream.current = media;
      const mime = ['audio/webm', 'audio/ogg', 'audio/mp4'].find((m) =>
        MediaRecorder.isTypeSupported(m),
      );
      if (!mime) throw Error('unsupported');
      const rec = new MediaRecorder(media, { mimeType: mime });
      recorder.current = rec;
      const parts = [];
      let size = 0;
      rec.ondataavailable = (e) => {
        size += e.data.size;
        if (size <= 2 * 1024 * 1024) parts.push(e.data);
        else {
          discard.current = true;
          stop();
          setState('idle');
          setMessage('Recording too large. Type a short note instead.');
        }
      };
      rec.onerror = () => {
        discard.current = true;
        release();
        setState('idle');
        setMessage('Recording failed. Type your note instead.');
      };
      rec.onstop = async () => {
        release();
        if (!active.current || discard.current) return;
        setState('processing');
        setMessage('Transcribing online… raw audio is not saved in this app.');
        const body = new FormData();
        body.append(
          'file',
          new Blob(parts, { type: mime }),
          mime === 'audio/mp4' ? 'note.m4a' : mime === 'audio/ogg' ? 'note.ogg' : 'note.webm',
        );
        body.append('language', language);
        body.append('consent_to_provider', 'true');
        try {
          const r = await api('/assistant/speech', { method: 'POST', body, timeout: 25000 });
          if (active.current) {
            if (r.transcript) change(r.transcript);
            setMessage(
              r.warning || 'Review the transcript before using it. No business fields changed.',
            );
          }
        } catch (e) {
          if (active.current) setMessage(e.message + ' Type your note instead.');
        } finally {
          parts.length = 0;
          if (active.current) setState('idle');
        }
      };
      rec.start(250);
      setState('recording');
      setMessage('Recording · stop when finished. Maximum 20 seconds.');
      timer.current = setTimeout(stop, 20000);
    } catch (e) {
      release();
      setState('idle');
      setMessage(
        e.name === 'NotAllowedError'
          ? 'Microphone permission denied. Type your note instead.'
          : 'Microphone unavailable. Type your note instead.',
      );
    }
  }
  return (
    <section className="panel" aria-label="Voice note preview">
      <p>Voice notes are optional. Check the transcript before using it, or type instead.</p>
      <label className="field">
        Speech language
        <select
          aria-label="Speech language"
          value={language}
          onChange={(e) => setLanguage(e.target.value)}
          disabled={state !== 'idle'}
        >
          <option value="en-IN">English · preview</option>
          <option value="hi-IN">Hindi · preview</option>
          <option value="kn-IN">Kannada · preview</option>
        </select>
      </label>
      <label className="check-field">
        <input
          type="checkbox"
          checked={consent}
          onChange={(e) => setConsent(e.target.checked)}
          disabled={state !== 'idle'}
        />
        Send this recording to Sarvam to turn it into text.
      </label>
      <div className="action-row">
        <button
          className="button secondary"
          type="button"
          disabled={!enabled || !consent || state !== 'idle'}
          onClick={start}
        >
          Start recording
        </button>
        <button
          className="button secondary"
          type="button"
          disabled={state !== 'recording' && state !== 'requesting'}
          onClick={() => {
            if (state === 'requesting') {
              discard.current = true;
              setState('idle');
              setMessage('Recording cancelled.');
            } else stop();
          }}
        >
          Stop recording
        </button>
      </div>
      {!enabled && <p>Voice notes are unavailable. Type your message instead.</p>}
      <p role="status" aria-live="polite">
        {message}
      </p>
    </section>
  );
}
export function Assistant({ follow }) {
  const [caps, setCaps] = useState(null),
    [question, setQuestion] = useState(''),
    [result, setResult] = useState(null),
    [error, setError] = useState(''),
    [busy, setBusy] = useState(false),
    [source, setSource] = useState(''),
    [target, setTarget] = useState('hi-IN'),
    [translation, setTranslation] = useState(null),
    [consent, setConsent] = useState(false),
    [reviewed, setReviewed] = useState(false);
  const [context, setContext] = useState('none'),
    [entities, setEntities] = useState([]),
    [entity, setEntity] = useState('');
  async function chooseContext(value) {
    setContext(value);
    setEntity('');
    setEntities([]);
    if (['case_read', 'stock_read', 'draft_followup'].includes(value))
      await run(async () => {
        setEntities(await api(value === 'stock_read' ? '/products' : '/cases'));
      });
  }
  useEffect(() => {
    api('/assistant/capabilities')
      .then(setCaps)
      .catch((e) => setError(e.message));
  }, []);
  async function run(fn) {
    setError('');
    setBusy(true);
    try {
      await fn();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="panel partner-screen">
      <h1>Merchant help & language</h1>
      <p>Get help with your store. Check any draft before using it.</p>
      {error && (
        <p role="alert" className="error-box">
          {error}
        </p>
      )}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          run(async () =>
            setResult(
              await api('/assistant/help', {
                method: 'POST',
                body: {
                  question,
                  purpose: 'merchant_help',
                  tool: context,
                  ...(entity ? { entity_id: entity } : {}),
                },
              }),
            ),
          );
        }}
      >
        <label className="field">
          Your question
          <textarea
            aria-label="Your question"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            required
            maxLength={800}
          />
        </label>
        <label className="field">
          Use a source
          <select
            aria-label="Use a source"
            value={context}
            onChange={(e) => chooseContext(e.target.value)}
          >
            <option value="none">Product/support sources only</option>
            <option value="brief_read">My recorded brief</option>
            <option value="case_read">A supplier case</option>
            <option value="stock_read">A stock SKU</option>
            <option value="draft_followup">Draft follow-up for an approved case</option>
          </select>
        </label>
        {['case_read', 'stock_read', 'draft_followup'].includes(context) && (
          <label className="field">
            Source record
            <select
              aria-label="Source record"
              value={entity}
              onChange={(e) => setEntity(e.target.value)}
              required
            >
              <option value="">
                {entities.length
                  ? 'Choose your recorded source'
                  : 'No records available; add one in the workflow first'}
              </option>
              {entities.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.invoice
                    ? `${r.invoice.supplier} · ${r.invoice.reference}`
                    : `${r.name} (${r.unit})`}
                </option>
              ))}
            </select>
          </label>
        )}
        <button
          className="button primary"
          disabled={
            busy ||
            !navigator.onLine ||
            (['case_read', 'stock_read', 'draft_followup'].includes(context) && !entity)
          }
        >
          {busy ? 'Checking…' : 'Ask for help'}
        </button>
      </form>
      {result && (
        <div aria-live="polite">
          <h2>Sources</h2>
          {result.retrieved_sources.map((d) => (
            <article key={d.document_id}>
              <h3>
                {d.title} · {d.section}
              </h3>
              <p>{d.text}</p>
              <a href={d.citation} target="_blank" rel="noreferrer">
                Read {d.title}
              </a>
              <p>Updated {d.reviewed_at}</p>
            </article>
          ))}
          <h2>Recorded store facts</h2>
          {!result.merchant_facts.length && (
            <p>
              No store records were requested. Use the linked purchase, stock or claim workflow for
              private facts.
            </p>
          )}
          {result.merchant_facts.map((fact, i) => (
            <article key={i}>
              <p>Recorded source: {fact.source_label || 'Linked store record'}</p>
              {fact.stock_quantity !== undefined && (
                <p>
                  Confirmed stock: {fact.stock_quantity} {fact.unit}
                </p>
              )}
              {fact.remaining_paise !== undefined && (
                <p>
                  Remaining claim: {money(fact.remaining_paise)} · {fact.status} · recorded recovery{' '}
                  {money(fact.recovered_paise)}
                </p>
              )}
              {fact.fact && <p>{fact.fact}</p>}
              <button className="button secondary" onClick={() => follow?.(fact.route)}>
                Review source record
              </button>
            </article>
          ))}
          {result.draft_action && (
            <section className="info-box">
              <p>{result.draft_action.text}</p>
              <p>
                Draft only · not sent. Open the approved source workflow to review and share
                explicitly.
              </p>
            </section>
          )}
          <h2>Explanation / limits</h2>
          <p>{result.general_explanation}</p>
          <p>{result.support_route}</p>
        </div>
      )}
      <h2>Translation draft</h2>
      <p>No message is sent here. Review the original beside the draft before copying.</p>
      <label className="field">
        Original message / voice note
        <textarea
          aria-label="Original message / voice note"
          value={source}
          onChange={(e) => {
            setSource(e.target.value);
            setTranslation(null);
            setReviewed(false);
          }}
          maxLength={2000}
        />
      </label>
      {caps?.speech_preview && (
        <VoiceNote
          enabled={caps.speech_preview}
          change={(v) => {
            setSource(v);
            setTranslation(null);
            setReviewed(false);
          }}
        />
      )}
      <label className="field">
        Translate to
        <select
          aria-label="Translate to"
          value={target}
          onChange={(e) => {
            setTarget(e.target.value);
            setTranslation(null);
            setReviewed(false);
          }}
        >
          <option value="hi-IN">Hindi · draft</option>
          <option value="kn-IN">Kannada · draft</option>
          <option value="en-IN">Original English</option>
        </select>
      </label>
      <label className="check-field">
        <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} />
        Send the text to Sarvam for this translation
      </label>
      <button
        className="button secondary"
        disabled={busy || !source || (!consent && target !== 'en-IN') || !navigator.onLine}
        onClick={() =>
          run(async () => {
            setReviewed(false);
            setTranslation(
              await api('/assistant/translate', {
                method: 'POST',
                body: { text: source, target, consent_to_provider: consent },
              }),
            );
          })
        }
      >
        Prepare translation draft
      </button>
      {translation && (
        <div className="translation-compare">
          <section>
            <h3>Source</h3>
            <p className="message-preview">{translation.source}</p>
          </section>
          <section>
            <h3>Draft · review required</h3>
            <p className="message-preview">
              {translation.draft ||
                'Unavailable. Use the original or enter a translation manually.'}
            </p>
          </section>
          {translation.warning && <p role="alert">{translation.warning}</p>}
          <label className="check-field">
            <input
              type="checkbox"
              checked={reviewed}
              onChange={(e) => setReviewed(e.target.checked)}
            />
            I reviewed the source, identifiers and amounts.
          </label>
          <button
            className="button secondary"
            disabled={!reviewed || !translation.draft || !translation.numeric_match}
            onClick={() =>
              run(async () => {
                await navigator.clipboard.writeText(translation.draft);
                setError('Reviewed draft copied; no message was sent.');
              })
            }
          >
            Copy reviewed translation
          </button>
        </div>
      )}
      <CachedHelp />
    </section>
  );
}
