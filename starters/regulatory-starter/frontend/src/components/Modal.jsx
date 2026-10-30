import React, { useEffect, useRef } from 'react';
import { X } from 'lucide-react';
function Modal({ title, subtitle, close, children, wide = false, closeDisabled = false }) {
  const ref = useRef(null),
    oldFocus = useRef(document.activeElement);
  useEffect(() => {
    ref.current?.focus();
    const old = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = old;
      oldFocus.current?.focus();
    };
  }, []);
  const keys = (e) => {
    if (e.key === 'Escape' && !closeDisabled) close();
    if (e.key === 'Tab') {
      const els = [
        ...ref.current.querySelectorAll(
          'button:not(:disabled),input:not(:disabled),select:not(:disabled),textarea:not(:disabled),a[href],[tabindex="0"]',
        ),
      ];
      const first = els[0],
        last = els[els.length - 1];
      if (!els.length) {
        e.preventDefault();
        ref.current?.focus();
        return;
      }
      if (
        e.shiftKey &&
        (document.activeElement === first || document.activeElement === ref.current)
      ) {
        e.preventDefault();
        last?.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first?.focus();
      }
    }
  };
  return (
    <div
      className="modal-backdrop"
      onMouseDown={(e) => !closeDisabled && e.target === e.currentTarget && close()}
    >
      <section
        className={`modal ${wide ? 'wide' : ''}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby="dialog-title"
        ref={ref}
        tabIndex={-1}
        onKeyDown={keys}
      >
        <div className="modal-header">
          <div>
            <h2 id="dialog-title">{title}</h2>
            {subtitle && <p>{subtitle}</p>}
          </div>
          <button
            className="icon-button"
            onClick={close}
            aria-label="Close dialog"
            disabled={closeDisabled}
          >
            <X size={20} />
          </button>
        </div>
        {children}
      </section>
    </div>
  );
}

export { Modal };
