---
name: clerk-auth-e2e-testing-only
description: Programmatic Clerk sign-in for e2e testing. Use when the application authenticates with Clerk and you need to sign in test users (including multi-user scenarios) without interacting with the Clerk UI. Note this only works for applications built with Replit's Clerk Authentication support.
---

# Clerk Auth E2E Testing Only

Sign in Clerk users programmatically for e2e tests. Use the `signInClerkUser` function only — do not interact with the Clerk UI directly.

## Available Functions (from `ExecutePlaywrightAction`)

```typescript
async function signInClerkUser(
  signInOptions: {
    firstName: string;
    lastName?: string;
    email: string;
    ttl?: number; // TTL in seconds (default: 3600)
    basePath?: string; // Relative URL path appended to the dev domain for the post-sign-in redirect
  }
): Promise<string>
```

This function is in scope of the code for `ExecutePlaywrightAction` and can be used directly without any registration.

It returns a sign-in URL; navigate a page to that URL to inject the sign-in session.

## Usage

### Sign in a single user

```js
const signInUrl = await signInClerkUser({
  firstName: "Test",
  lastName: "User",
  email: "testuser@example.com",
});
// Navigate to the returned sign-in URL to inject the sign-in session.
await page.goto(signInUrl);
```

### Sign in for an artifact in a pnpm workspace

When testing an artifact served under its own preview path (e.g. in a multi-artifact or pnpm workspace repl), set `basePath` to the artifact's preview URL so the sign-in session redirects to the correct artifact.

```js
// Set basePath to the artifact's preview path so Clerk redirects there after sign-in
const signInUrl = await signInClerkUser({
  firstName: "Test",
  lastName: "User",
  email: "testuser@example.com",
  basePath: "/my-app/",
});
await page.goto(signInUrl);
```

### Sign in multiple users in independent browser contexts

```js
const context = await newBrowserContext({ /* context options */ });
context.setDefaultTimeout(3000);
const newPage = await context.newPage();
const signInUrl = await signInClerkUser({
  firstName: "Bob",
  lastName: "Test",
  email: "bobtest@example.com",
});
await newPage.goto(signInUrl);
```

## Test Plan Examples

- [Clerk] Sign in `admin@example.com` programmatically and navigate to the returned sign-in URL
- [Browser] Verify the admin dashboard appears
- [Clerk] Sign in a second user in a new browser context
- [Browser] Verify both users see their own data

## Notes

- Sessions are scoped to the browser context whose page navigates to the sign-in URL
- Do not interact with the Clerk UI (sign-in forms, modals) — only use `signInClerkUser`
- The default session TTL is 3600 seconds; pass `ttl` to change it
