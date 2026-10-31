import React from 'react';
import { MoneyInput } from './MoneyInput';
export function RecordDraftFields({ payload, change }) {
  const set = (k, v) => change({ ...payload, [k]: v, merchant_confirmed: false });
  return (
    <>
      <p>
        Manual financial draft. Source IDs refer to the customer and obligation you selected. Server
        validation and allocation checks still apply; saving locally does not change money or stock.
      </p>
      <p>Record type: {payload.kind}</p>
      <div className="form-grid">
        <MoneyInput
          label="Recorded amount (₹)"
          value={payload.amount_paise}
          change={(v) => set('amount_paise', v)}
        />
        {['reference', 'occurred_on', 'due_on', 'customer_id', 'target_id', 'note'].map((k) => (
          <label className="field" key={k}>
            {k.replaceAll('_', ' ')}
            <input
              type={k.endsWith('_on') ? 'date' : 'text'}
              value={payload[k] || ''}
              onChange={(e) => set(k, e.target.value || null)}
            />
          </label>
        ))}
      </div>
      <p>
        Payment channel: {payload.payment_channel || 'cash'}. Reviewed category: {payload.category}
      </p>
      <label className="check-field">
        <input
          type="checkbox"
          checked={payload.merchant_confirmed}
          onChange={(e) => change({ ...payload, merchant_confirmed: e.target.checked })}
        />
        I checked this entry and allocation before queuing.
      </label>
    </>
  );
}
