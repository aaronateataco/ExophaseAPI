---
name: monetization
description: Router for payments, checkout, subscriptions, paywalls, ecommerce, online stores, physical goods, and monetization. Read this before searching integrations or calling ProposeIntegration to present billing options. After the user chooses, continue with the Shopify, Stripe, Whop, or RevenueCat skill.
---

# Monetization

Read this before searching integrations or proposing billing options. Use `ProposeIntegration` to present connector-backed choices, then hand off to skill `shopify`, `stripe`, `whop`, or `revenuecat` after the user chooses. Do not re-litigate the choice inside those skills.

Providers:

- **Shopify** — best for physical goods; handles inventory, shipping, and checkout out of the box.
- **Stripe** — most flexible; requires external Stripe-dashboard setup to go live.
- **Whop** — fastest; auto-provisioned store and checkout, no external dashboard.
- **RevenueCat** — native-mobile in-app purchases only (Expo / React Native / iOS). Not for plain web apps.

## Skip the routing question if any of these is true

The provider is already known — do not ask, just hand off to the matching provider skill.

- User explicitly named Shopify, Stripe, Whop, or RevenueCat. (Generic words — "payments", "subscriptions", "paywall", "monetize", "let users pay" — do NOT count.)
- A provider is already integrated: a `SHOPIFY_*` / `STRIPE_*` / `WHOP_*` / `REVENUECAT_*` env var or Replit Configuration is set.
- The integration for `shopify-store`, `stripe`, `whop`, or `revenuecat` is already connected.
- The conversation already established a provider.
- The user is asking for follow-up CRUD on an existing payment integration.
- The user explicitly asks for native in-app purchases or digital goods consumed in a mobile app → RevenueCat is the only supported provider. If it is not connected, resolve it with `searchIntegrations({ query: "revenuecat" })` and propose that candidate, then hand off to the `revenuecat` skill. Do not offer Stripe or Whop for native IAP.
- The user's intent is clearly to sell **physical goods** (shipping-required items or inventory-based products) → Hand off to the `shopify` skill. Signals:
  - Explicit mention of physical/tangible items, inventory management, stock, shipping, or fulfillment.
  - A concrete tangible product noun, even when the user never says the word "physical". Treat nouns like pens, shirts, t-shirts, apparel, clothing, mugs, books, ceramics, pottery, jewelry, candles, soap, posters, prints, stickers, accessories, merch, or merchandise as physical-goods signals. "Build an ecommerce site for selling pens with checkout and payments" is a Shopify request — route to `shopify` and recommend the Shopify Store integration + Shopify-hosted checkout, NOT a custom Stripe/Express checkout.
  - **Digital/download exception (takes priority over the tangible-noun shortcut):** if the same item is sold as a digital file, download, print-on-demand digital asset, PDF, template, or other intangible deliverable — e.g. "downloadable poster prints", "printable sticker pack", "ebook" — it is NOT physical goods. A digital/download cue overrides the product noun: do not hand off to `shopify`. For plain web, let the user choose between Stripe and Whop. For digital goods consumed in a native-mobile app, use the RevenueCat rule above.
  - Generic storefront language without a clear physical or digital signal is ambiguous. Do not ask a separate clarification; include Shopify alongside Stripe and Whop, and use each candidate's reason to explain the tradeoff.

## Otherwise, let the user choose a provider

The connector shortlist allowlist is **Shopify, Stripe, and Whop**. For native-mobile / Expo / React Native apps or iOS IAP, **RevenueCat** is also allowlisted. Do not add any other provider returned by a generic integration search (including Square or Squareup). Never offer RevenueCat for plain web apps. If the user names another provider, say it isn't available through this flow and offer the allowlisted options instead.

### Propose the options in one step (preferred)

Propose the connector-backed providers together so a single click both chooses and connects:

1. Resolve the integration ids with **per-provider** `searchIntegrations` calls:
   - If the request does not establish whether commerce is physical or digital, search Shopify, Stripe, and Whop. For native-mobile apps, also search RevenueCat.
   - For clearly digital plain-web requests, search Stripe and Whop.
   - Explicit physical-goods and native-IAP requests use the direct-provider rules above instead of a shortlist.
   If any provider comes back already attached (`status: "added"`), it is the provider-known case from above — stop and hand off to that provider's skill instead of proposing. Otherwise use the returned `connector:<id>` (`status: "not_setup"`) or `connection:<id>` (`status: "not_added"`) for each provider; skip providers with no result or an `added` result, and never fabricate an id. Do not call `addIntegration` for shortlist candidates before selection: pass the returned ids directly to `ProposeIntegration`, then continue only with the selected provider's skill and injected connection setup.
2. Call the `ProposeIntegration` model tool with a `proposal` shortlist of the candidates that resolved (2-5), each with a one-line `reason`, e.g.:

   ```json
   {
     "proposal": [
       { "integrationId": "connector:<shopify-ccfg-id>", "reason": "Best for physical goods and storefronts" },
       { "integrationId": "connector:<stripe-ccfg-id>", "reason": "Most flexible" },
       { "integrationId": "connector:<whop-ccfg-id>", "reason": "Fastest, no external setup" }
     ]
   }
   ```

   The user picks one candidate and that single click connects it — there is no follow-up confirm step.
3. If only one provider's search returned an integration, call `ProposeIntegration` with `{ "proposal": [{ "integrationId": "<returned-id>" }] }` instead (still no separate question). If none resolved, tell the user no billing connector is available in this workspace rather than presenting a fake choice.
4. After the user connects, continue with the matching provider skill (`stripe` / `whop` / `shopify` / `revenuecat`). It will see the connection is already established and proceed to build, skipping its own re-proposal.

### Native-mobile provider shortlist

Generic native-mobile / Expo / React Native billing requests use the same physical-versus-digital rules as web, then add RevenueCat to the candidates. An ambiguous native-mobile request therefore includes Shopify, Stripe, Whop, and RevenueCat; explicit native IAP still routes directly to RevenueCat. The user's selection connects the provider, then hand off to its skill.
