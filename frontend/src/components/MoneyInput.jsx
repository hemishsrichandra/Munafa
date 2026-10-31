import React, { useEffect, useId, useRef, useState } from 'react';
import { useLanguage } from '../language';
import { parseRupeeInput, rupeeInput } from '../api';

export function MoneyInput({ label, value, change, signed = false }) {
  const { t } = useLanguage();
  const [text, setText] = useState(() => rupeeInput(value));
  const input = useRef(null);
  const hint = useId();
  useEffect(() => {
    if (parseRupeeInput(text, signed) !== (value ?? null)) setText(rupeeInput(value));
  }, [value, signed]);
  const invalid = text !== '' && parseRupeeInput(text, signed) === null;
  useEffect(() => {
    input.current?.setCustomValidity(
      invalid ? 'Enter a valid rupee amount with up to two decimal places.' : '',
    );
  }, [invalid]);
  return (
    <label className="field">
      {t(label)}
      <input
        ref={input}
        aria-label={t(label)}
        aria-describedby={invalid ? hint : undefined}
        type="text"
        inputMode="decimal"
        value={text}
        pattern={signed ? '-?[0-9]+([.][0-9]{0,2})?' : '[0-9]+([.][0-9]{0,2})?'}
        aria-invalid={invalid || undefined}
        onChange={(e) => {
          setText(e.target.value);
          change(parseRupeeInput(e.target.value, signed));
        }}
      />
      {invalid && <small id={hint}>Enter a rupee amount with up to two decimal places.</small>}
    </label>
  );
}
