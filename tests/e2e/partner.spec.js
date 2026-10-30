const { test, expect } = require('@playwright/test');
async function login(page) {
  await page.goto('/');
  await page.getByLabel('Username', { exact: true }).fill('partner-owner');
  await page.getByLabel('Password', { exact: true }).fill('isolated-browser-test-password');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Daily business brief' })).toBeVisible();
}
async function request(page, path, body) {
  return page.evaluate(
    async ({ path, body }) => {
      const csrf = decodeURIComponent(
        document.cookie
          .split('; ')
          .find((s) => s.startsWith('pbp_csrf='))
          ?.split('=')[1] || '',
      );
      const r = await fetch('/api' + path, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': csrf,
          'Idempotency-Key': crypto.randomUUID(),
        },
        body: JSON.stringify(body),
      });
      if (!r.ok) throw Error(await r.text());
      return r.json();
    },
    { path, body },
  );
}
test('evidence brief and synthetic settlement reconciliation are usable on phones', async ({
  page,
}) => {
  await page.setViewportSize({ width: 360, height: 800 });
  await login(page);
  await expect(page.getByText('No connected Paytm data', { exact: true })).toBeVisible();
  await request(page, '/products', {
    code: 'BRIEF-RICE',
    name: 'Brief Rice',
    unit: 'kg',
    reorder_threshold: '2',
  });
  await page.getByRole('button', { name: 'More', exact: true }).click();
  await page.getByRole('button', { name: 'Payments & reconciliation', exact: true }).click();
  await page
    .getByRole('button', { name: 'Load isolated synthetic payment demo', exact: true })
    .click();
  await expect(
    page.getByRole('heading', { name: 'SYNTHETIC DEMO DATA', exact: true }),
  ).toBeVisible();
  await expect(page.getByText(/Recorded payout differs from known components/)).toBeVisible();
  for (const width of [320, 360, 390, 430]) {
    await page.setViewportSize({ width, height: 844 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
      true,
    );
  }
  await page.getByRole('button', { name: 'Home', exact: true }).click();
  await expect(
    page.getByRole('heading', { name: 'Check stock: Brief Rice', exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole('heading', { name: 'Review settlement components', exact: true }),
  ).toBeVisible();
  for (const width of [320, 360, 390, 430]) {
    await page.setViewportSize({ width, height: 844 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
      true,
    );
  }
  await page.screenshot({ path: 'artifacts/test-evidence/batch6-brief-phone.png', fullPage: true });
  const stock = page
    .getByRole('article')
    .filter({ has: page.getByRole('heading', { name: 'Check stock: Brief Rice' }) });
  await stock.getByRole('button', { name: 'Review source' }).click();
  await expect(page.getByRole('heading', { name: /movement history/ })).toBeVisible();
});
module.exports = { login, request };

test('cited help, unsupported answers, reviewed translation and microphone denial', async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await login(page);
  await page.route('**/api/assistant/capabilities', (route) =>
    route.fulfill({ json: { speech_preview: true, cloud_configured: false } }),
  );
  await page.addInitScript(() => {
    Object.defineProperty(navigator, 'mediaDevices', {
      configurable: true,
      value: {
        getUserMedia: async () => {
          throw new DOMException('denied', 'NotAllowedError');
        },
      },
    });
  });
  // Apply the permission-denial stub without relying on browser/device permissions.
  await page.evaluate(() => {
    Object.defineProperty(navigator, 'mediaDevices', {
      configurable: true,
      value: {
        getUserMedia: async () => {
          throw new DOMException('denied', 'NotAllowedError');
        },
      },
    });
  });
  await page.getByRole('button', { name: 'More', exact: true }).click();
  await page.getByRole('button', { name: 'Merchant help & language', exact: true }).click();
  await page
    .getByLabel('Your question', { exact: true })
    .fill('How does physical receiving update stock?');
  await page.getByRole('button', { name: 'Ask grounded help', exact: true }).click();
  await expect(page.getByRole('link', { name: /Source product-receiving-v1/ })).toBeVisible();
  await request(page, '/products', { code: 'HELP-RICE', name: 'Help Rice', unit: 'kg' });
  await page.getByLabel('Use a source', { exact: true }).selectOption('stock_read');
  await page.getByLabel('Source record', { exact: true }).selectOption({ label: 'Help Rice (kg)' });
  await page.getByRole('button', { name: 'Ask grounded help', exact: true }).click();
  await expect(page.getByText('Confirmed stock: 0 kg', { exact: true })).toBeVisible();

  await page.getByLabel('Your question', { exact: true }).fill('guarantee a loan');
  await page.getByRole('button', { name: 'Ask grounded help', exact: true }).click();
  await expect(
    page.getByText(/No current, consistent approved source answers this question/),
  ).toBeVisible();
  await page
    .getByText(
      'I agree to send this recording to Sarvam for transcription. Check provider retention settings before use.',
      { exact: true },
    )
    .click();
  await page.getByRole('button', { name: 'Start recording', exact: true }).click();
  await expect(
    page.getByText('Microphone permission denied. Type your note instead.', { exact: true }),
  ).toBeVisible();
  await page.evaluate(() => {
    Object.defineProperty(navigator, 'mediaDevices', {
      configurable: true,
      value: {
        getUserMedia: async () => ({
          getTracks: () => [
            {
              stop: () => {
                window.__testTrackStopped = true;
              },
            },
          ],
        }),
      },
    });
    window.MediaRecorder = class {
      static isTypeSupported() {
        return true;
      }
      constructor() {
        this.state = 'inactive';
      }
      start() {
        this.state = 'recording';
      }
      stop() {
        this.state = 'inactive';
        this.ondataavailable?.({ data: new Blob([new Uint8Array([26, 69, 223, 163])]) });
        this.onstop?.();
      }
    };
  });
  await page.route('**/api/assistant/speech', (route) =>
    route.fulfill({
      json: {
        transcript: 'Uncertain noisy note — check manually',
        review_required: true,
        warning: 'Mock noisy recognition: review before use.',
      },
    }),
  );
  await page.getByRole('button', { name: 'Start recording', exact: true }).click();
  await expect(
    page.getByText('Recording · stop when finished. Maximum 20 seconds.', { exact: true }),
  ).toBeVisible();
  await page.getByRole('button', { name: 'Stop recording', exact: true }).click();
  await expect(page.getByLabel('Original message / voice note', { exact: true })).toHaveValue(
    'Uncertain noisy note — check manually',
  );
  expect(await page.evaluate(() => window.__testTrackStopped)).toBe(true);
  await page
    .getByLabel('Original message / voice note', { exact: true })
    .fill('Reviewed original 80');
  await page.getByLabel('Translate to', { exact: true }).selectOption('en-IN');
  await page.getByRole('button', { name: 'Prepare translation draft', exact: true }).click();
  const copy = page.getByRole('button', { name: 'Copy reviewed translation', exact: true });
  await expect(copy).toBeDisabled();
  await page.getByText('I reviewed the source, identifiers and amounts.', { exact: true }).click();
  await expect(copy).toBeEnabled();
  for (const width of [320, 360, 390, 430]) {
    await page.setViewportSize({ width, height: 844 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
      true,
    );
  }
  await page.screenshot({ path: 'artifacts/test-evidence/batch7-help-phone.png', fullPage: true });
  await page.getByRole('button', { name: 'Review source record', exact: true }).click();
  await expect(page.getByRole('heading', { name: /Help Rice · movement history/ })).toBeVisible();
});

test('P2 readiness stays blocked and links only recorded store history on phones', async ({
  page,
}) => {
  await page.setViewportSize({ width: 360, height: 800 });
  await login(page);
  await request(page, '/products', { code: 'P2-READINESS', name: 'Readiness Rice', unit: 'kg' });
  await page.getByRole('button', { name: 'More', exact: true }).click();
  await page.getByRole('button', { name: 'Planning readiness', exact: true }).click();
  await expect(
    page.getByRole('heading', { name: 'Planning readiness', exact: true }),
  ).toBeVisible();
  await expect(page.getByText('Disabled · prerequisites unproven', { exact: true })).toHaveCount(3);
  await page
    .getByLabel('Recorded SKU to inspect', { exact: true })
    .selectOption({ label: 'Readiness Rice (kg)' });
  await page
    .getByRole('button', { name: 'Inspect procurement prerequisites', exact: true })
    .click();
  await expect(
    page.getByRole('heading', { name: 'Readiness check only', exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText('No proposal created · No external action performed · Consent not verified', {
      exact: true,
    }),
  ).toBeVisible();
  await page.getByLabel('Readiness purpose', { exact: true }).selectOption('lender_checklist');
  await page.getByRole('button', { name: 'Inspect financial prerequisites', exact: true }).click();
  await expect(
    page.getByText(
      'No lender-authorised, purpose-bound consent can be verified. This check does not register consent or submit data.',
      { exact: true },
    ),
  ).toBeVisible();
  await page.getByLabel('Comparison readiness', { exact: true }).selectOption('peer_comparison');
  await page
    .getByRole('button', { name: 'Inspect benchmarking prerequisites', exact: true })
    .click();
  await expect(page.getByText(/All peer results are suppressed/)).toBeVisible();
  for (const width of [320, 360, 390, 430]) {
    await page.setViewportSize({ width, height: 844 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
      true,
    );
  }
  await page.screenshot({
    path: 'artifacts/test-evidence/batch9-readiness-phone.png',
    fullPage: true,
  });
  await page
    .getByRole('button', { name: 'Review Readiness Rice movement history', exact: true })
    .click();
  await expect(
    page.getByRole('heading', { name: /Readiness Rice · movement history/ }),
  ).toBeVisible();
  // New readiness requests fail visibly; they are not silently queued as orders.
  await page.getByRole('button', { name: 'More', exact: true }).click();
  await page.getByRole('button', { name: 'Planning readiness', exact: true }).click();
  await expect(page.getByText('Disabled · prerequisites unproven', { exact: true })).toHaveCount(3);
  await page.route('**/api/planning/readiness', (route) =>
    route.fulfill({ status: 503, json: { detail: 'Readiness service temporarily unavailable.' } }),
  );
  await page.getByRole('button', { name: 'Refresh readiness', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('Readiness service temporarily unavailable.');
});
