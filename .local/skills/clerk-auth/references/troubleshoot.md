# Clerk Auth — Troubleshooting

Use this reference when the user reports that Clerk Auth is broken, misbehaving, or not doing what they expect. It works hand-in-hand with `setup-and-customization.md` — the most reliable fix is almost always to diff the user's current Clerk wiring against the canonical snippets in that reference and bring the code back in line.

This reference assumes `checkClerkManagementStatus` returned `managed`.

## First: Confirm Where the Issue Is Seen

The fix path is very different for dev vs. prod, so you need to know which environment the issue is in before doing anything else. Skip this step in either of these cases:

- The user already said which environment they're seeing the issue in (e.g. "the published app is broken", "preview won't load", "in production…").
- You're handling Clerk-related errors surfaced in the console logs while addressing the user's request — those always come from the dev environment, so treat the issue as **Dev (preview)**.

Otherwise, call the `AskQuestion` model tool with explicit choices so the response preserves the environment label:

```json
{
  "question": "Where are you seeing this Clerk issue?",
  "choices": ["Dev (preview)", "Prod (published app)"]
}
```

If the issue is in **Prod (published app)**, keep in mind that Replit-managed Clerk has a lot of setup that differs between dev and prod, so it is often misleading to guess at production behavior from the dev setup. For example:

- Prod uses the proxy, dev does not.
- Prod uses a different set of Clerk keys that are swapped in at publish time and are not visible from dev.
- Prod has more moving parts than dev — domains, DNS, SSO provider credentials, etc.

Rely on user-reported observations from the published app (error text, failing URL, browser console / network output) and a code diff against the canonical snippets in `setup-and-customization.md` instead of workspace logs or workspace secrets.

## The Most Common Culprit: Code Divergence

The vast majority of Clerk Auth issues are caused by the user's Clerk-related code having diverged from the canonical code in `setup-and-customization.md` — typically from earlier edits, half-applied refactors, or out-of-date Clerk SDK patterns. The single most reliable fix is to **re-load the clerk-auth skill** (even if it is already open in this conversation, so you pick up the latest canonical snippets) and resync against `setup-and-customization.md`:

1. **Update the `@clerk/*` packages first** to the latest version allowed by the workspace's `minimumReleaseAge` policy in `pnpm-workspace.yaml`. The skill is sometimes updated to fix issues or adopt features that depend on newer SDK versions, so the canonical snippets you're about to diff against may assume an SDK newer than what the user has installed.
2. **Then diff the user's code against `setup-and-customization.md`** and apply the minimum edit to the Clerk-related configuration code that brings it back to the canonical shape — without changing the user's existing design, features, or unrelated code.
3. **Finalize and ask the user to retry**:
   - **Dev (preview) only:** Restart both backend and frontend workflows. Still restart even if no changes were made in Step 2 — occasionally the issue is caused by newly set-up Clerk secrets not being baked into the frontend without a restart. Then ask the user to retry.
   - **Prod (published app) only:** Ask the user to verify the change doesn't break the preview app, then re-publish the app and retry.

Common symptoms that should immediately trigger a diff against the canonical code:

- Clerk authentication doesn't work at all on the preview app:
  - preview doesn't load
  - Failed to load Clerk JS
  - sign-in doesn't work on preview app
- Preview app works, but the published app doesn't:
  - Published app doesn't load on web or Expo client.
  - Published app client tries to load Clerk files from a domain other than the proxy URL `https://<app_domain>/api/__clerk`.
  - API requests don't authenticate (return 401 Unauthorized).
  - User can't sign in across the app's domains.

When you see any of these, do **not** start theorizing about specific causes — re-load the skill, read `setup-and-customization.md` from disk, and diff. The canonical snippets can change between conversations, so there's no harm in loading the latest copy to make sure you're diffing against the current source of truth rather than what you remember.

## Specific Known Symptoms

Issues where the code-divergence diff above won't find the bug because the root cause sits in adjacent infrastructure, not in Clerk's own wiring.

### Sign-in form hangs / Turnstile error 300030

Clerk embeds a Cloudflare Turnstile iframe (`challenges.cloudflare.com`) for bot protection. If the app sets a CSP (Helmet on Express, or a CSP meta tag), the iframe is blocked silently and the form hangs. Tell: console shows `[Cloudflare Turnstile] Error: 300030`. No Helmet/CSP in the codebase → not this bug.

Fix: add `challenges.cloudflare.com` and Clerk's own domains to `frame-src`, `connect-src`, and `script-src`. See `references/web-migration.md` § "CSP blocks Clerk or Cloudflare Turnstile" for the directive list.

## Red Herrings — Symptoms That Look Broken But Are Expected

The following are **not** bugs. Do not "fix" them, do not edit the related code, and do not edit the related secrets. Explain to the user that the behavior is expected.

- **Publishable key starts with `pk_test` in dev.** Expected. Replit-managed Clerk uses test keys (`pk_test` / `sk_test`) during development and automatically swaps in live keys (`pk_live` / `sk_live`) when the app is published. Do not edit the keys manually.
- **Console says "Clerk has been loaded with development keys" or otherwise warns about development keys.** Expected for the same reason as above. This is a normal Clerk development warning, not a misconfiguration.
- **User can't sign in to the published app with the account they made in dev (or vice versa).** Expected. Dev and prod have completely separate user stores — accounts and data do not cross over. The user needs to sign up again in the published app.
- **Server-side proxy code only runs in production / `CLERK_PROXY_URL` is empty or not defined in dev.** Expected. The dev app talks to the Clerk dev FAPI directly, without going through the proxy — the proxy is production-only. Do not ask for or set proxy-related env vars in dev.

If the user is convinced one of the above is the bug, gently explain why it isn't, then redirect to the actual user-visible symptom and re-evaluate against the divergence section above.

## Dangerous Fixes / Actions — Things Likely to Make Things Worse

The following fixes and actions almost always cause more breakages than they resolve. Do not take them unless the user has explicitly asked for them and you have explained the risk.

- **Hand-editing the existing Clerk-managed secrets** (`CLERK_SECRET_KEY`, `CLERK_PUBLISHABLE_KEY`, `VITE_CLERK_PUBLISHABLE_KEY`, `EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY`, `CLERK_PROXY_URL`) — including renaming, replacing, or rotating their values. These are auto-provisioned by `setupClerkWhitelabelAuth()` and are swapped to live values automatically at publish time; manual edits tend to break parts of the integration that aren't visible to the agent. This is **not** a blanket ban on environment / deployment code: bringing canonical wiring code back in line (e.g. restoring `EXPO_PUBLIC_CLERK_PROXY_URL` forwarding in `build.js`, fixing client `proxyUrl`, re-syncing `clerkMiddleware` setup) is exactly the diff-against-canonical fix the previous section calls for.
- **Pushing the user toward opening their own Clerk account on the Clerk dashboard when they did not explicitly ask for it.** Replit-managed Clerk is the default and does not require Clerk dashboard access. Do not redirect the user to `dashboard.clerk.com` to "fix" things — that switches them to a fundamentally different (external) Clerk setup that this skill does not cover.
- **Making non-trivial functional changes to `clerkProxyMiddleware`.** This middleware is load-bearing for the published app and any divergence from the canonical implementation tends to break prod silently. Always re-sync it to the latest version in the skill before proposing any fix on it; if the canonical version doesn't fix the issue, look elsewhere first.
- **Calling `setAuthTokenGetter` in a web client.** This function is only meant for standalone app clients (e.g. Expo) where cookies don't work. The web app uses Clerk session cookies that the browser sends automatically — wiring `setAuthTokenGetter` on web doesn't fix 401s and usually adds new failure modes. The fix for web 401s lives in middleware order and `requireAuth`, not the client.
