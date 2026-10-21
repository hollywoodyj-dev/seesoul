'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const handler = require('../api/seesoul-payment-status.js');

const config = {linkId: 'plink_MOCKSEESOUL', priceId: 'price_MOCKSEESOUL', liveMode: false};
const correctSession = () => ({object: 'checkout.session', mode: 'payment', payment_link: config.linkId, livemode: false, amount_total: 15000, currency: 'aud', status: 'complete', payment_status: 'paid', metadata: {brand: 'SEESOUL', service_code: 'SEESOUL_COUNSELLING_60'}});
const correctItems = () => [{price: {id: config.priceId}, quantity: 1, amount_total: 15000}];
const status = (session, items = correctItems()) => handler.statusForSession(session, items, config);

test('exact SeeSoul 60 min purchase paid is verified', () => assert.equal(status(correctSession()), 'paid'));
test('1320 payment link is rejected even at AUD 150', () => assert.equal(status({...correctSession(), payment_link: 'plink_MOCK1320'}), 'unverified'));
test('1320 checkout metadata is rejected', () => assert.equal(status({...correctSession(), metadata: {brand: '1320', service_code: 'SEESOUL_COUNSELLING_60'}}), 'unverified'));
test('different product/price is rejected', () => assert.equal(status(correctSession(), [{price: {id: 'price_OTHER'}, quantity: 1, amount_total: 15000}]), 'unverified'));
test('wrong amount is rejected', () => assert.equal(status({...correctSession(), amount_total: 10000}), 'unverified'));
test('wrong currency is rejected', () => assert.equal(status({...correctSession(), currency: 'usd'}), 'unverified'));
test('unpaid is pending, not paid', () => assert.equal(status({...correctSession(), payment_status: 'unpaid'}), 'pending'));
test('open session is not paid', () => assert.notEqual(status({...correctSession(), status: 'open'}), 'paid'));
test('test/live Stripe environments must match', () => assert.equal(status({...correctSession(), livemode: true}), 'unverified'));
test('2 items are rejected', () => assert.equal(status(correctSession(), [...correctItems(), ...correctItems()]), 'unverified'));
test('wrong quantity is rejected', () => assert.equal(status(correctSession(), [{price: {id: config.priceId}, quantity: 2, amount_total: 15000}]), 'unverified'));
test('missing metadata is rejected', () => assert.equal(status({...correctSession(), metadata: {}}), 'unverified'));
test('missing config fails closed', () => assert.equal(handler.getStripeConfig({}), null));

const ids = {SEESOUL_COUNSELLING_PAYMENT_LINK_ID: 'plink_X', SEESOUL_COUNSELLING_PRICE_ID: 'price_X'};
test('restricted test key is accepted as test mode', () => assert.equal(handler.getStripeConfig({...ids, STRIPE_SECRET_KEY: 'rk_' + 'test_' + 'abc123'}).liveMode, false));
test('restricted live key is accepted as live mode', () => assert.equal(handler.getStripeConfig({...ids, STRIPE_SECRET_KEY: 'rk_' + 'live_' + 'abc123'}).liveMode, true));
test('publishable key is rejected', () => assert.equal(handler.getStripeConfig({...ids, STRIPE_SECRET_KEY: 'pk_' + 'live_' + 'abc123'}), null));

const sid = 'cs_test_AAAAAAAAAAAAAAAA';
const KEY = 'rk_' + 'test_' + 'FAKESECRET123';
function response() {
  const r = {code: 200, headers: {}, body: null};
  r.setHeader = (k, v) => { r.headers[k] = v; };
  r.status = (c) => { r.code = c; return r; };
  r.json = (b) => { r.body = b; return r; };
  return r;
}
const fixture = (o = {}) => ({...correctSession(), payment_link: 'plink_SEESOULTEST', ...o});
const items = (price = 'price_SEESOULTEST') => ({object: 'list', has_more: false, data: [{price: {id: price}, quantity: 1, amount_total: 15000}]});
async function run({id = sid, session = fixture(), listing = items(), failFetch = false, method = 'GET'} = {}) {
  const keys = ['STRIPE_SECRET_KEY', 'SEESOUL_COUNSELLING_PAYMENT_LINK_ID', 'SEESOUL_COUNSELLING_PRICE_ID'];
  const oldEnv = Object.fromEntries(keys.map((k) => [k, process.env[k]]));
  const oldFetch = global.fetch;
  let calls = 0;
  try {
    process.env.STRIPE_SECRET_KEY = KEY;
    process.env.SEESOUL_COUNSELLING_PAYMENT_LINK_ID = 'plink_SEESOULTEST';
    process.env.SEESOUL_COUNSELLING_PRICE_ID = 'price_SEESOULTEST';
    global.fetch = async (url, opts) => {
      calls++;
      assert.ok(url.startsWith('https://api.stripe.com/v1/checkout/sessions/'));
      assert.equal(opts.headers.Authorization, 'Bearer ' + KEY);
      if (failFetch) throw new Error('Simulated upstream failure');
      return {ok: true, json: async () => (url.includes('/line_items?') ? listing : session)};
    };
    const res = response();
    await handler({method, query: {session_id: id}}, res);
    assert.equal(res.headers['Cache-Control'], 'no-store, private, max-age=0');
    return {res, calls};
  } finally {
    global.fetch = oldFetch;
    for (const [k, v] of Object.entries(oldEnv)) { if (v === undefined) delete process.env[k]; else process.env[k] = v; }
  }
}

test('endpoint verifies a valid Stripe payment', async () => { const {res, calls} = await run(); assert.equal(res.code, 200); assert.deepEqual(res.body, {status: 'paid'}); assert.equal(calls, 2); });
test('endpoint rejects a 1320 payment without claiming paid', async () => { const {res} = await run({session: fixture({payment_link: 'plink_1320'})}); assert.deepEqual(res.body, {status: 'unverified'}); });
test('endpoint reports unpaid as pending', async () => { const {res} = await run({session: fixture({payment_status: 'unpaid'})}); assert.deepEqual(res.body, {status: 'pending'}); });
test('endpoint rejects an invalid ID before calling Stripe', async () => { const {res, calls} = await run({id: '../../../../'}); assert.equal(res.code, 400); assert.equal(calls, 0); });
test('endpoint does not leak Stripe errors', async () => { const {res} = await run({failFetch: true}); assert.equal(res.code, 502); assert.deepEqual(res.body, {status: 'unverified'}); });
test('endpoint rejects a wrong price ID', async () => { const {res} = await run({listing: items('price_1320')}); assert.deepEqual(res.body, {status: 'unverified'}); });
test('endpoint rejects more line items than one', async () => { const {res} = await run({listing: {...items(), has_more: true}}); assert.deepEqual(res.body, {status: 'unverified'}); });
test('endpoint rejects test/live mismatch without calling Stripe', async () => { const {res, calls} = await run({id: 'cs_live_AAAAAAAAAAAAAAAA'}); assert.deepEqual(res.body, {status: 'unverified'}); assert.equal(calls, 0); });
test('endpoint rejects unsupported methods', async () => { const {res, calls} = await run({method: 'POST'}); assert.equal(res.code, 405); assert.equal(calls, 0); });
test('endpoint fails closed when not configured', async () => {
  const old = process.env.STRIPE_SECRET_KEY; delete process.env.STRIPE_SECRET_KEY;
  const res = response(); await handler({method: 'GET', query: {session_id: sid}}, res);
  if (old !== undefined) process.env.STRIPE_SECRET_KEY = old;
  assert.equal(res.code, 503); assert.deepEqual(res.body, {status: 'unverified'});
});

const page = fs.readFileSync(path.join(__dirname, '..', 'payment-success.html'), 'utf8');
const block = (state) => page.match(new RegExp('<div[^>]*data-pay-state="' + state + '"[^>]*>'))[0];
test('hidden payment states cannot be revealed by theme.css display rules', () => {
  assert.ok(/\[data-pay-state\]\[hidden\]\s*\{\s*display:\s*none\s*!important;?\s*\}/.test(page));
});
test('page shows only the unverified state without JavaScript', () => {
  assert.ok(!/hidden/.test(block('unverified')));
  for (const s of ['checking', 'paid', 'pending']) assert.ok(/\shidden(\s|>)/.test(block(s)), s);
});
test('page never claims receipt outside the verified branch', () => {
  const visible = page.replace(/<script[\s\S]*?<\/script>/g, '').replace(/<div[^>]*data-pay-state="paid"[^>]*>[\s\S]*?<\/div>/, '');
  assert.ok(!visible.includes('已收到'));
  assert.ok(!visible.includes('付款已经收到'));
});
test('page keeps appointment and consent separate in every state', () => {
  assert.ok(page.includes('付款成功不代表预约时间已经确认，也不代表已经完成知情同意书签署'));
  assert.ok(page.includes('避免重复付款'));
});
test('page has no 1320 reference and no secret', () => {
  assert.ok(!page.includes('1320'));
  assert.ok(!/(sk|rk)_(live|test)_/.test(page));
});
