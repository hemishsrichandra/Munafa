// Adapted from Munafa's bounded API client. Browser-only starter.
const isNative = () => false;
let nativeToken = '';
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
      .find((v) => v.startsWith('rp_csrf='))
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
