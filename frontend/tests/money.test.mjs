import test from 'node:test';
import assert from 'node:assert/strict';
import { money, parseRupeeInput, rupeeInput } from '../src/api.js';
test('paise formatting preserves normal rupees, cents and negative differences', () => {
  assert.equal(money(0), '₹0');
  assert.equal(money(8000), '₹80');
  assert.equal(money(820), '₹8.20');
  assert.equal(money(-2001), '-₹20.01');
  assert.equal(money(12345678), '₹1,23,456.78');
});
test('large safe integer paise retains the exact cent rather than a divided float', () => {
  assert.ok(money(9000000000000001).endsWith('.01'));
  assert.ok(money(9000000000000099).endsWith('.99'));
});
test('unavailable or invalid money is never presented as a zero ledger value', () => {
  assert.equal(money(null), 'Not recorded');
  assert.equal(money(), 'Not recorded');
  for (const p of [NaN, Infinity, 1.5, Number.MAX_SAFE_INTEGER + 1, '8000'])
    assert.equal(money(p), 'Amount unavailable');
});
test('merchant rupee entry preserves exact cents, null and signed rounding', () => {
  assert.equal(parseRupeeInput('80.05'), 8005);
  assert.equal(parseRupeeInput('0'), 0);
  assert.equal(parseRupeeInput('1.'), 100);
  assert.equal(parseRupeeInput('-0.25', true), -25);
  for (const value of ['', '-', '-1', '1.001', '1e2', 'NaN', '1,000', '900719925474099.99'])
    assert.equal(parseRupeeInput(value), null);
  for (const value of [0, 1, -25, 8005, 9000000000000001])
    assert.equal(parseRupeeInput(rupeeInput(value), true), value);
  assert.equal(rupeeInput(null), '');
});
