import { money } from './api';

export function saveEvidence(c) {
  // The app renders a shareable card from approved, server-calculated evidence.
  const canvas = document.createElement('canvas');
  canvas.width = 1000;
  canvas.height = 510 + c.invoice.lines.length * 130;
  const ctx = canvas.getContext('2d');
  const W = 1000;
  ctx.fillStyle = '#f8f8f1';
  ctx.fillRect(0, 0, W, canvas.height);
  ctx.fillStyle = '#254b34';
  ctx.fillRect(0, 0, W, 125);
  ctx.fillStyle = '#fff';
  ctx.font = 'bold 48px sans-serif';
  ctx.fillText('munafa.', 55, 80);
  ctx.font = '18px sans-serif';
  ctx.fillText(c.synthetic ? 'SYNTHETIC DEMO EVIDENCE' : 'MERCHANT-APPROVED EVIDENCE', 440, 77);
  ctx.fillStyle = '#254b34';
  ctx.font = 'bold 65px sans-serif';
  ctx.fillText(money(c.approved_amount_paise), 55, 220);
  ctx.font = '24px sans-serif';
  ctx.fillText(c.invoice.supplier.slice(0, 60), 55, 275);
  ctx.font = '21px sans-serif';
  ctx.fillText(`Invoice ${c.invoice.reference} · ${c.invoice.date}`, 55, 317);
  c.invoice.lines.forEach((l, i) => {
    const y = 380 + i * 130;
    ctx.fillStyle = '#d6ddd0';
    ctx.fillRect(55, y - 20, 890, 1);
    ctx.fillStyle = '#20362a';
    ctx.font = 'bold 24px sans-serif';
    ctx.fillText(l.name.slice(0, 62), 55, y + 20);
    ctx.font = '22px sans-serif';
    ctx.fillText(
      `${l.billed} billed - ${l.received} received = ${l.billed - l.received} ${l.unit}`,
      55,
      y + 57,
    );
    ctx.fillText(
      `${l.billed - l.received} x ${money(l.price_paise)} = ${money((l.billed - l.received) * l.price_paise)}`,
      55,
      y + 90,
    );
  });
  const base = 410 + c.invoice.lines.length * 130;
  ctx.fillStyle = '#516253';
  ctx.font = '18px sans-serif';
  ctx.fillText(
    `Merchant confirmed completed delivery and effective prices. Case ${c.id}`,
    55,
    base,
  );
  ctx.fillText(
    `Approved evidence version ${c.approved_version}. Merchant-reported counts; no supplier acceptance implied.`,
    55,
    base + 33,
  );
  canvas.toBlob((blob) => {
    if (!blob) return;
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `munafa-${c.id}-evidence.png`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 5000);
  }, 'image/png');
}
