import { Capacitor } from '@capacitor/core';
let nativeToken = '';
export function clearNativeSession() {
  nativeToken = '';
}
export const isNative = () => Capacitor.isNativePlatform();
export async function api(path, options = {}) {
  const { body, timeout = 20000, signal: parentSignal, ...rest } = options;
  const base = import.meta.env.VITE_API_BASE || '/api';
  if (isNative() && !/^https:\/\//.test(base))
    throw new Error('Your store connection is not set up. Ask your administrator for help.');
  const controller = new AbortController(),
    timer = setTimeout(() => controller.abort(), timeout);
  const cancel = () => controller.abort();
  parentSignal?.addEventListener('abort', cancel, { once: true });
  if (parentSignal?.aborted) controller.abort();
  const method = (rest.method || 'GET').toUpperCase();
  const csrf =
    document.cookie
      .split('; ')
      .find((v) => v.startsWith('pbp_csrf='))
      ?.split('=')
      .slice(1)
      .join('=') || '';
  try {
    const response = await fetch(`${base}${path}`, {
      ...rest,
      signal: controller.signal,
      credentials: 'include',
      headers: {
        ...(body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
        ...(method === 'GET'
          ? {}
          : { 'X-CSRF-Token': decodeURIComponent(csrf), 'Idempotency-Key': crypto.randomUUID() }),
        ...(isNative() ? { 'X-Client-Platform': 'android' } : {}),
        ...(nativeToken ? { Authorization: `Bearer ${nativeToken}` } : {}),
        ...rest.headers,
      },
      ...(body !== undefined
        ? { body: body instanceof FormData ? body : JSON.stringify(body) }
        : {}),
    });
    let result;
    try {
      result = await response.json();
    } catch {
      throw new Error(
        'The server response was incomplete. Keep your draft and retry the same operation.',
      );
    }
    if (!response.ok) {
      const detail = result.detail;
      const error = new Error(
        Array.isArray(detail)
          ? detail.map((d) => `${d.loc.slice(1).join('.')}: ${d.msg}`).join(' · ')
          : detail || 'Request failed. Please retry.',
      );
      error.status = response.status;
      throw error;
    }
    if (isNative() && result.session_token) nativeToken = result.session_token;
    return result;
  } catch (error) {
    if (error.status) throw error;
    throw new Error(
      navigator.onLine
        ? 'Cannot confirm server acceptance. Keep this operation and retry when connected.'
        : 'You are offline. Save a device draft in Drafts & sync; direct server changes have not been confirmed.',
    );
  } finally {
    clearTimeout(timer);
    parentSignal?.removeEventListener('abort', cancel);
  }
}
// Format integer paise without a floating division that can round large cents.
// Missing/invalid amounts must never masquerade as a confirmed zero balance.
export const money = (p = null) => {
  if (!Number.isSafeInteger(p)) return p == null ? 'Not recorded' : 'Amount unavailable';
  const digits = Math.abs(p).toString().padStart(3, '0');
  const whole = Number(digits.slice(0, -2)),
    cents = digits.slice(-2);
  return `${p < 0 ? '-' : ''}₹${new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 }).format(whole)}${cents === '00' ? '' : '.' + cents}`;
};
export const day = (s) =>
  s
    ? new Date(`${s.slice(0, 10)}T12:00:00`).toLocaleDateString('en-IN', {
        day: 'numeric',
        month: 'short',
      })
    : '—';
export const today = () =>
  new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Kolkata',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(new Date());
export function download(name, text, type = 'text/plain') {
  const url = URL.createObjectURL(new Blob([text], { type }));
  const a = document.createElement('a');
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 5000);
}

export async function exportLedger() {
  let a = await api('/actions', { method: 'POST', body: { action_type: 'export_ledger' } });
  a = await api(`/actions/${a.id}/approve`, {
    method: 'POST',
    body: { version: a.version, payload_digest: a.payload_digest },
  });
  return api(`/actions/${a.id}/execute`, { method: 'POST', body: { version: a.version } });
}

// Native private files use the authenticated connection, then an explicit OS share sheet.
// Tokens never appear in file URLs; temporary files are removed when the sheet closes.
export async function saveBlob(blob, name) {
  if (!isNative()) {
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = name;
    anchor.click();
    setTimeout(() => URL.revokeObjectURL(url), 5000);
    return;
  }
  const { Filesystem, Directory } = await import('@capacitor/filesystem');
  const { Share } = await import('@capacitor/share');
  const data = await new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result.split(',')[1]);
    reader.onerror = () => reject(new Error('Unable to prepare file. Please retry.'));
    reader.readAsDataURL(blob);
  });
  const path = `${crypto.randomUUID()}-${name.replace(/[^a-zA-Z0-9._-]/g, '_')}`;
  const file = await Filesystem.writeFile({ path, data, directory: Directory.Cache });
  try {
    await Share.share({ files: [file.uri], dialogTitle: 'Save or share this file' });
  } finally {
    await Filesystem.deleteFile({ path, directory: Directory.Cache });
  }
}
export async function downloadPrivate(path, name, returnBlob = false) {
  if (!path.startsWith('/api/')) throw new Error('Unsupported private file path.');
  const base = import.meta.env.VITE_API_BASE || '/api';
  if (isNative() && !/^https:\/\//.test(base))
    throw new Error('Your store connection is not set up. Ask your administrator for help.');
  let response;
  try {
    response = await fetch(`${base}${path.slice(4)}`, {
      credentials: 'include',
      headers: nativeToken ? { Authorization: `Bearer ${nativeToken}` } : {},
    });
  } catch {
    throw new Error('Cannot download this private file while disconnected.');
  }
  if (!response.ok) throw new Error('File unavailable or access denied. Refresh and try again.');
  const disposition = response.headers.get('Content-Disposition') || '';
  const filename = name || disposition.match(/filename="?([^";]+)"?/)?.[1] || 'merchant-evidence';
  const blob = await response.blob();
  if (returnBlob) return blob;
  await saveBlob(blob, filename);
}

// Decimal UI conversion only; authoritative amounts are calculated on the server.
export function paiseFromInput(value) {
  if (!/^\d+(?:\.\d{0,2})?$/.test(value)) return 0;
  const [whole, fraction = ''] = value.split('.');
  const paise = Number(whole) * 100 + Number(fraction.padEnd(2, '0'));
  return Number.isSafeInteger(paise) ? paise : 0;
}

// Presentation boundary only: exact decimal text to integer paise, never rounding.
export function parseRupeeInput(value, signed = false) {
  const pattern = signed ? /^-?\d+(?:\.\d{0,2})?$/ : /^\d+(?:\.\d{0,2})?$/;
  if (!pattern.test(value)) return null;
  const negative = value.startsWith('-');
  const [whole, cents = ''] = (negative ? value.slice(1) : value).split('.');
  const paise = Number(whole) * 100 + Number(cents.padEnd(2, '0'));
  return Number.isSafeInteger(paise) ? (negative ? -paise : paise) : null;
}
export function rupeeInput(paise) {
  if (!Number.isSafeInteger(paise)) return '';
  const digits = Math.abs(paise).toString().padStart(3, '0');
  return `${paise < 0 ? '-' : ''}${digits.slice(0, -2)}.${digits.slice(-2)}`;
}

export const getPurchases = () => api('/purchases');
export const getPurchase = (id) => api(`/purchases/${id}`);
export const createManualPurchase = (draft) =>
  api('/purchases/manual', { method: 'POST', body: draft });
export const editPurchase = (id, version, draft) =>
  api(`/purchases/${id}`, { method: 'PATCH', body: { version, draft } });
export const createReceiving = (id, payload) =>
  api(`/purchases/${id}/receivings`, { method: 'POST', body: payload });
export const getProducts = () => api('/products');
export const createProduct = (product) => api('/products', { method: 'POST', body: product });
export const getMovements = (id) => api(`/products/${id}/movements`);
export const getExpiry = () => api('/inventory/expiry');
export async function proposeCommerceAction(
  action_type,
  entity_id,
  expected_version,
  payload = {},
) {
  let a = await api('/commerce/proposals', {
    method: 'POST',
    body: { action_type, entity_id, expected_version, payload },
  });
  a = await api(`/actions/${a.id}/approve`, {
    method: 'POST',
    body: { version: a.version, payload_digest: a.payload_digest },
  });
  return api(`/actions/${a.id}/execute`, { method: 'POST', body: { version: a.version } });
}
export const acceptPurchase = (id, version) =>
  proposeCommerceAction('accept_purchase', id, version);
export const acceptReceiving = (id, version) =>
  proposeCommerceAction('accept_receiving', id, version);
