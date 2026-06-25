# Stripe setup — designer membership (1-year subscriptions)

Global Designer Hub uses **Stripe Checkout** for designer memberships. Yearly billing is the default (e.g. Personal Designer Website **$790/year**).

## 1. Stripe account

1. Create or sign in at [Stripe Dashboard](https://dashboard.stripe.com/).
2. Use **Test mode** while developing.

## 2. API keys

From **Developers → API keys**, add to `.env`:

```env
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...
```

## 3. Create membership prices

Either create Products/Prices manually in Stripe, or run:

```bash
python manage.py setup_stripe_membership_prices
```

This creates three products with **monthly** and **yearly** recurring prices:

| Plan | Monthly | Yearly (1 year) |
|------|---------|-----------------|
| Professional Portfolio | $29 | $290 |
| Personal Designer Website | $79 | $790 |
| Premium Fashion Studio | $149 | $1,490 |

Paste the printed `STRIPE_PRICE_*` values into `.env`.

Preview without Stripe:

```bash
python manage.py setup_stripe_membership_prices --dry-run
```

## 4. Webhook (required for activation)

1. **Developers → Webhooks → Add endpoint**
2. URL: `https://your-domain.com/payment/stripe/webhook/`
3. Events:
   - `checkout.session.completed`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_succeeded`
   - `setup_intent.succeeded`
4. Copy the signing secret to `.env`:

```env
STRIPE_WEBHOOK_SECRET=whsec_...
```

For local dev, use the [Stripe CLI](https://stripe.com/docs/stripe-cli):

```bash
stripe listen --forward-to localhost:8004/payment/stripe/webhook/
```

## 5. Customer portal (optional)

Enable **Billing → Customer portal** in Stripe so designers can update cards and invoices via **Manage in Stripe** on the dashboard.

## 6. Designer flow

1. Register / log in as a designer
2. **Dashboard → Membership Plans** (`/subscription/`)
3. Choose plan (yearly selected by default)
4. **Select Plan** → Stripe Checkout (card, Link, Apple Pay, Google Pay)
5. After payment, redirect includes `session_id`; membership activates immediately
6. Confirmation email sent; renewal date shown for 1-year plans

## 7. Verify

```bash
python manage.py test designer_portfolio.tests.SubscriptionPaymentTests
```

Use Stripe test card `4242 4242 4242 4242`, any future expiry, any CVC.
