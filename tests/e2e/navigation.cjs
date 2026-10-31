const { expect } = require('@playwright/test');
async function merchantNavigate(page, destination) {
  const nav = page.getByRole('navigation', { name: 'Main navigation', exact: true });
  await nav.getByRole('button', { name: 'More', exact: true }).click();
  const labels = {
    'Credit cases': 'Missing Items & Refunds',
    Suppliers: 'Supplier details',
    Insights: 'Money returned',
  };
  const button = page.getByRole('button', { name: labels[destination], exact: true });
  await expect(button).toBeVisible();
  await button.click();
}
module.exports = { merchantNavigate };
