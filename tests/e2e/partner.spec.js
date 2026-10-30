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
  await page.getByRole('button', { name: 'Load sample settlements', exact: true }).click();
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
  await page.getByRole('button', { name: 'Ask for help', exact: true }).click();
  await expect(
    page.getByRole('link', { name: 'Read Munafa product guide' }).first(),
  ).toHaveAttribute('href', '/api/assistant/sources/product-receiving-v1');
  await request(page, '/products', { code: 'HELP-RICE', name: 'Help Rice', unit: 'kg' });
  await page.getByLabel('Use a source', { exact: true }).selectOption('stock_read');
  await page.getByLabel('Source record', { exact: true }).selectOption({ label: 'Help Rice (kg)' });
  await page.getByRole('button', { name: 'Ask for help', exact: true }).click();
  await expect(page.getByText('Confirmed stock: 0 kg', { exact: true })).toBeVisible();

  await page.getByLabel('Your question', { exact: true }).fill('guarantee a loan');
  await page.getByRole('button', { name: 'Ask for help', exact: true }).click();
  await expect(
    page.getByText(/No current, consistent approved source answers this question/),
  ).toBeVisible();
  await page
    .getByText('Send this recording to Sarvam to turn it into text.', { exact: true })
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

test('stock planning shows merchant rules, preserves P2 gates and links recorded history', async ({
  page,
}) => {
  await page.setViewportSize({ width: 360, height: 800 });
  await login(page);
  await request(page, '/products', { code: 'P2-READINESS', name: 'Readiness Rice', unit: 'kg' });
  // Developer diagnostics left the UI; their financial/consent gates must still hold.
  const response = await page.request.get('/api/planning/readiness');
  const readiness = await response.json();
  expect(
    readiness.capabilities.every(
      (c) => c.status === 'disabled' && !c.available && !c.external_execution_enabled,
    ),
  ).toBe(true);
  for (const [capability, intent] of [
    ['procurement', 'purchase_order_draft'],
    ['financial_planning', 'lender_checklist'],
    ['benchmarking', 'peer_comparison'],
  ]) {
    const gate = await request(page, '/planning/assess', { capability, intent });
    expect(gate.assessment_only).toBe(true);
    expect(gate.proposal_created).toBe(false);
    expect(gate.external_action_performed).toBe(false);
    expect(gate.consent_verified).toBe(false);
    expect(gate.financial_decision).toBeNull();
    expect(gate.peer_statistics).toBeNull();
  }
  await page.getByRole('button', { name: 'More', exact: true }).click();
  await page.getByRole('button', { name: 'Stock planning', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Stock planning', exact: true })).toBeVisible();
  await expect(
    page
      .getByRole('article')
      .filter({ hasText: 'Readiness Rice · kg' })
      .getByText('Not enough sales history for a forecast.', { exact: true }),
  ).toBeVisible();
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
  await page.getByRole('button', { name: 'More', exact: true }).click();
  await page.getByRole('button', { name: 'Stock planning', exact: true }).click();
  await expect(
    page
      .getByRole('article')
      .filter({ hasText: 'Readiness Rice · kg' })
      .getByText('Not enough sales history for a forecast.', { exact: true }),
  ).toBeVisible();
  await page.route('**/api/intelligence/readiness', (route) =>
    route.fulfill({
      status: 503,
      json: { detail: 'Stock information is temporarily unavailable.' },
    }),
  );
  await page.getByRole('button', { name: 'Refresh products', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText(
    'Stock information is temporarily unavailable.',
  );
});
