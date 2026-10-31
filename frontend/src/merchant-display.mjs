// Compare saved decimal quantities for display only; never post calculated stock.
export function hasMissingItems(purchase) {
  if (!purchase.delivery_complete) return false;
  const fixed = (value) => {
    const match = /^(\d+)(?:\.(\d{1,6}))?$/.exec(String(value));
    return match ? BigInt(match[1]) * 1000000n + BigInt((match[2] || '').padEnd(6, '0')) : null;
  };
  return (purchase.lines || []).some((line) => {
    const billed = fixed(line.billed_quantity),
      received = fixed(line.received_quantity);
    return billed !== null && received !== null && received < billed;
  });
}
