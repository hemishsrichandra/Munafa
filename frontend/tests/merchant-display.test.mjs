import test from 'node:test';
import assert from 'node:assert/strict';
import { hasMissingItems } from '../src/merchant-display.mjs';
test('missing badge requires final confirmed counts and exact comparable quantities', () => {
  const p = {
    delivery_complete: true,
    lines: [
      { billed_quantity: '10000000000000.000002', received_quantity: '10000000000000.000001' },
    ],
  };
  assert.equal(hasMissingItems(p), true);
  assert.equal(hasMissingItems({ ...p, delivery_complete: false }), false);
  assert.equal(
    hasMissingItems({
      delivery_complete: true,
      lines: [{ billed_quantity: '2.500000', received_quantity: '2.5' }],
    }),
    false,
  );
  assert.equal(
    hasMissingItems({
      delivery_complete: true,
      lines: [{ billed_quantity: '2.5', received_quantity: null }],
    }),
    false,
  );
});
