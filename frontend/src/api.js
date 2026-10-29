export async function api(path, options = {}) {
  const { body, ...rest } = options;
  const response = await fetch(`/api${path}`, {
    ...rest,
    headers: body instanceof FormData ? {} : { 'Content-Type': 'application/json' },
    ...(body !== undefined ? { body: body instanceof FormData ? body : JSON.stringify(body) } : {}),
  });
  let result;
  try {
    result = await response.json();
  } catch {
    throw new Error('The server returned an unreadable response.');
  }
  if (!response.ok) {
    const detail = result.detail;
    throw new Error(
      Array.isArray(detail)
        ? detail.map((d) => `${d.loc.slice(1).join('.')}: ${d.msg}`).join(' · ')
        : detail || 'Request failed. Please retry.',
    );
  }
  return result;
}
export const money = (p = 0) =>
  new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: p % 100 ? 2 : 0,
  }).format(p / 100);
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
