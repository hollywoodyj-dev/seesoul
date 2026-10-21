'use strict';
/** GET /api/seesoul-payment-status — read-only Stripe Checkout Session check. Stores nothing, books nothing. */
const SESSION_ID_RE = /^cs_(test|live)_[a-zA-Z0-9]{10,250}$/;
const CODE = 'SEESOUL_COUNSELLING_60';

function getStripeConfig(env) {
  const secret = env.STRIPE_SECRET_KEY || '';
  const linkId = env.SEESOUL_COUNSELLING_PAYMENT_LINK_ID || '';
  const priceId = env.SEESOUL_COUNSELLING_PRICE_ID || '';
  if (!/^(rk|sk)_(test|live)_[a-zA-Z0-9]+$/.test(secret) ||
      !/^plink_[a-zA-Z0-9]+$/.test(linkId) ||
      !/^price_[a-zA-Z0-9]+$/.test(priceId)) return null;
  return {secret, linkId, priceId, liveMode: /^(rk|sk)_live_/.test(secret)};
}

function isCorrectPurchase(session, items, config) {
  return Boolean(session && Array.isArray(items) &&
    session.object === 'checkout.session' &&
    session.mode === 'payment' &&
    session.payment_link === config.linkId &&
    session.livemode === config.liveMode &&
    session.amount_total === 15000 &&
    String(session.currency || '').toLowerCase() === 'aud' &&
    session.metadata?.brand === 'SEESOUL' &&
    session.metadata?.service_code === CODE &&
    items.length === 1 &&
    items[0]?.price?.id === config.priceId &&
    items[0]?.quantity === 1 &&
    items[0]?.amount_total === 15000);
}

function statusForSession(session, items, config) {
  if (!isCorrectPurchase(session, items, config)) return 'unverified';
  if (session.status === 'complete' && session.payment_status === 'paid') return 'paid';
  if (session.payment_status === 'unpaid') return 'pending';
  return 'unverified';
}

async function stripeGet(endpoint, secret) {
  const response = await fetch('https://api.stripe.com/v1/' + endpoint, {
    method: 'GET',
    headers: {Authorization: 'Bearer ' + secret, Accept: 'application/json'},
    signal: AbortSignal.timeout(8000),
  });
  if (!response.ok) throw new Error('Stripe request failed (' + response.status + ')');
  return response.json();
}

function reply(res, statusCode, payload) {
  res.setHeader('Cache-Control', 'no-store, private, max-age=0');
  res.setHeader('Content-Type', 'application/json; charset=utf-8');
  res.setHeader('X-Content-Type-Options', 'nosniff');
  return res.status(statusCode).json(payload);
}

async function handler(req, res) {
  if (req.method !== 'GET') {
    res.setHeader('Allow', 'GET');
    return reply(res, 405, {status: 'unverified'});
  }
  const sessionId = req.query?.session_id;
  if (typeof sessionId !== 'string' || !SESSION_ID_RE.test(sessionId)) {
    return reply(res, 400, {status: 'unverified'});
  }
  const config = getStripeConfig(process.env);
  if (!config) return reply(res, 503, {status: 'unverified'});
  if (sessionId.startsWith('cs_live_') !== config.liveMode) {
    return reply(res, 200, {status: 'unverified'});
  }
  try {
    const path = 'checkout/sessions/' + encodeURIComponent(sessionId);
    const session = await stripeGet(path, config.secret);
    // limit=2 so a multi-item session is rejected instead of judged by its first item.
    const listing = await stripeGet(path + '/line_items?limit=2', config.secret);
    if (listing.has_more || !Array.isArray(listing.data)) return reply(res, 200, {status: 'unverified'});
    return reply(res, 200, {status: statusForSession(session, listing.data, config)});
  } catch (_) {
    return reply(res, 502, {status: 'unverified'});
  }
}

module.exports = handler;
module.exports.getStripeConfig = getStripeConfig;
module.exports.isCorrectPurchase = isCorrectPurchase;
module.exports.statusForSession = statusForSession;
