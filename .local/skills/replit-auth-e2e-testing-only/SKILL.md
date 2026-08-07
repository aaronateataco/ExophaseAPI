---
name: replit-auth-e2e-testing-only
description: Configure OIDC test credentials for apps using Replit Auth (or a standard OIDC provider). Use when overriding ISSUER_URL or setting login claims for multi-user e2e tests — not for other auth providers. You MUST read this skill if you suspect the application being tested uses Replit Auth. Ideally this should take place before the browser page is even loaded, since the bypass likely would require restarting the workflows.
---

# Replit Auth E2E Testing Only

Configure OIDC authentication for multi-user e2e tests without manual login. This applies to Replit Auth and may not work for other providers — try logging in first to confirm how the app authenticates.

## Workflow Restarts

Before setting OIDC login claims, the workflow under test must allow the testing OIDC endpoint as a redirect URL.

1. Copy `/home/runner/workspace/.local/testing-agent/replit-auth.example.env` (it overrides `ISSUER_URL`).
2. Restart the workflow with `WorkflowsRestart`, setting `env_file` to the copied file's path.
3. Restart the **API server** AND *any* client workflows so the override is fully applied.

## Available Functions (from `ExecutePlaywrightAction`)

- `setNextOIDCLoginClaims(context, claims)` — configure auth bypass for the next login
- `clearNextOIDCLoginClaims(context)` — remove auth bypass

Those functions are in scope of the code for `ExecutePlaywrightAction` and can be used directly without any registration.

## How It Works

1. Set claims on a browser context → later logins in that context use those claims
2. App redirects to OIDC → bypass applies → redirects to the post-login page
3. Claims persist until changed or cleared
4. No claims set → login fails → redirects to `/`

## Usage

### Set claims

```js
await setNextOIDCLoginClaims(context, {
  sub: "unique_normal_user_id",
  email: "normal@example.com",
  first_name: "Normal",
  last_name: "Person"
});

// In this step or the next, the login credentials are applied automatically for as long as the claims are set for the context until cleared.

await page.goto('/login');
await page.getByTestId('login-button').click();
// User is logged in with the configured claims
```

### Clear claims

```js
await clearNextOIDCLoginClaims(context);
// Next login fails and redirects to /
```

## Test Plan Examples

- [OIDC] Set next login claims `{sub: "admin_id", email: "admin@example.com"}` for the current browser context
- [Browser] Click login and verify the admin dashboard appears
- [OIDC] Clear next login claims
- [Browser] Attempt login and verify redirect to `/`

## Notes

- Claims are scoped to a browser context
- Do not mock authentication directly — only use these functions
- Claims stay active across pages in that context until cleared
- If the override does not take hold for whatever reason, you may see an actual login screen instead of the bypass
