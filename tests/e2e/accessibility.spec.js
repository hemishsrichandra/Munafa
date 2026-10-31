const { test, expect } = require('@playwright/test');
const AxeBuilder = require('@axe-core/playwright').default;
const fs = require('node:fs');
test('WCAG AA automated scans on merchant destinations and bill dialog', async ({ page }) => {
  test.setTimeout(120000);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  await page.getByLabel('Username', { exact: true }).fill('records-owner');
  await page.getByLabel('Password', { exact: true }).fill('isolated-browser-test-password');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  const nav = page.getByRole('navigation', { name: 'Main navigation', exact: true });
  const violations = [];
  for (const label of ['Today · आज', 'Deliveries & Stock', 'Customer Khata', 'More · अन्य']) {
    await nav.getByRole('button', { name: label, exact: true }).click();
    await expect(page.getByRole('main')).toBeVisible();
    const result = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
      .analyze();
    violations.push(
      ...result.violations.map((v) => ({
        screen: label,
        id: v.id,
        nodes: v.nodes.map((n) => ({ target: n.target, summary: n.failureSummary })),
      })),
    );
  }
  await nav.getByRole('button', { name: 'Today · आज', exact: true }).click();
  await page
    .getByRole('button', { name: /New Bill/ })
    .first()
    .click();
  await expect(page.getByRole('dialog')).toBeVisible();
  const result = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
    .analyze();
  violations.push(
    ...result.violations.map((v) => ({
      screen: 'Bill dialog',
      id: v.id,
      nodes: v.nodes.map((n) => ({ target: n.target, summary: n.failureSummary })),
    })),
  );
  fs.mkdirSync('artifacts/test-evidence', { recursive: true });
  fs.writeFileSync(
    'artifacts/test-evidence/merchant-accessibility.json',
    JSON.stringify(violations, null, 2),
  );
  expect(violations).toEqual([]);
});
