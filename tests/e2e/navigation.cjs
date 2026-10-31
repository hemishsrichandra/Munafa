const { expect } = require('@playwright/test');
async function merchantNavigate(page, destination) {
  const nav = page.getByRole('navigation', { name: 'Main navigation', exact: true });
  await nav.getByRole('button', { name: 'More · अन्य', exact: true }).click();
  const labels = {
    'Credit cases': 'Missing Items & Refunds · कम सामान का पैसा',
    Suppliers: 'Supplier details · सप्लायर',
    Insights: 'Money returned · वापस मिला पैसा',
  };
  const button = page.getByRole('button', { name: labels[destination], exact: true });
  await expect(button).toBeVisible();
  await button.click();
}
module.exports = { merchantNavigate };
