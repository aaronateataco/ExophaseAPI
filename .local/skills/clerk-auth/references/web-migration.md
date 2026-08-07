# Web Migration: Replit Auth → Clerk (Legacy Fullstack JS)

This guide covers what to remove and what to transition for the Express API server and React+Vite web frontend. When adding Clerk code, refer to the `clerk-auth` skill for implementation details.

## Migration Philosophy

This migration **swaps the identity provider** from Replit Auth to Clerk. The app's structure, data model, and user lookup logic should remain as close to the original as possible:

- **Same bridge column**: however the app currently resolves an authenticated session to a local user row (by `id`, by `email`, etc.), use the same column with Clerk.
- **Same users table**: keep it active for app-specific state (roles, permissions, relationships). Only stop populating columns that overlap with what Clerk manages.
- **Same authorization logic**: role checks, permission guards, and app-column reads stay unchanged — they just get the user from a different source.
- **Same provisioning behavior**: preserve whatever the original app does on first login — don't auto-provision rows if it didn't, don't skip provisioning if it did.

Clerk replaces the login/session machinery. Everything else stays — but two things change shape, and both are sources of post-migration bugs if Replit Auth assumptions are ported verbatim:

- **Identity and authorization separate.** Under Replit Auth, sessions were created by your app's OIDC callback — so any invariant linking session validity to local-DB state (e.g., "every session has a user row," "every session is allowlisted") was enforced in your own code, before the session was issued. Under Clerk, session issuance moves to Clerk's servers and your app is no longer in that path. Identity (Clerk session) and authorization (local row, role, allowlist) become independently resolvable, and the two can disagree.
- **The client gains an async loading state.** Replit Auth had no client auth library; Clerk does, and it takes a moment to validate the session on page load. Code that fetches identity on mount must wait for it.

## Pre-Migration: Audit Existing Auth and API Calls

Before making code changes, inspect the existing auth and API client code to determine three things:

### 1. Identify the bridge column

Read the `upsertUser()` function (or equivalent verify/callback logic) and determine: **which column does the app use to link a Replit Auth session to a local user row?**

| What you find in the existing code | Bridge type | Clerk equivalent (from session token) |
| --- | --- | --- |
| `id: claims.sub` in upsertUser (blueprint default) | ID bridge | `sessionClaims.userId` |
| Lookup by `email` matching `claims.email` | Email bridge | `sessionClaims.email` |
| Lookup by `username` matching `claims.username` | Username bridge | `sessionClaims.username` |

The Clerk middleware you write must use the **same bridge column** as the existing code. Do not change how the app finds its local user row — just change where the lookup value comes from. 

**Do not assume `users.id` is the bridge field.** Some apps use a random UUID primary key and store the bridge field elsewhere. That bridge can still be the Replit Auth user ID, just on a different column; in that case, query that column with `sessionClaims.userId`. All bridge values are available directly in `sessionClaims` (no Clerk API call needed).

### Session claims reference

The session token is pre-configured during app setup with all fields needed for local DB lookups and identity display:

| Session field | Value | Use for |
| --- | --- | --- |
| `sessionClaims.userId` | Legacy Replit Auth subject ID (externalId) for migrated users, Clerk native ID for new users | Replit Auth subject ID bridge: `WHERE <the column that used to store claims.sub> = ?` |
| `sessionClaims.email` | User's primary email | Email bridge: `WHERE users.email = ?` |
| `sessionClaims.username` | Username | Username bridge: `WHERE users.username = ?` |
| `sessionClaims.firstName` | First name | Display / identity |
| `sessionClaims.lastName` | Last name | Display / identity |
| `auth.userId` | Clerk native ID (`user_2abc...`) | **Clerk API calls ONLY — never for local DB** |

**WARNING: Never pass `sessionClaims.userId` to Clerk API methods** (e.g., `clerkClient.users.getUser()`). It is a legacy local DB ID, not a Clerk ID. Clerk will return a 404. Use `auth.userId` exclusively for Clerk API calls. In practice, you should rarely need to call the Clerk API in the request path — `sessionClaims` has everything needed for the bridge and basic identity display.

### 2. Classify users table columns

Inspect the users table schema and classify each column:

**Clerk User object fields (identity — stop populating locally after migration):**

| Field | Clerk accessor (server) | Clerk accessor (React) |
| --- | --- | --- |
| Email | `user.primaryEmailAddress.emailAddress` | `user?.primaryEmailAddress?.emailAddress` |
| First name | `user.firstName` | `user?.firstName` |
| Last name | `user.lastName` | `user?.lastName` |
| Avatar / profile image | `user.imageUrl` | `user?.imageUrl` |
| Phone number | `user.primaryPhoneNumber.phoneNumber` | `user?.primaryPhoneNumber?.phoneNumber` |
| Password | Managed internally — never exposed | N/A |
| Last sign-in time | `user.lastSignInAt` | `user?.lastSignInAt` |
| Account creation time | `user.createdAt` | `user?.createdAt` |
| External ID (migration) | `user.externalId` | `user?.externalId` |
| Custom metadata | `user.publicMetadata` / `user.privateMetadata` | `user?.publicMetadata` |

- **Identity columns** (Clerk owns): any column whose data is in the table above. Common examples: `email`, `username`, `name`/`firstName`/`lastName`, `profileImageUrl`/`profile_picture`, `last_login_at`/`last_login`
- **App columns** (keep in local DB — continue reading/writing): everything else. Common examples: `role`, `permissions`, `is_active`, `title`, relationships like `agent_id`, subscription data, preferences, and any other business-logic fields

**How to handle identity columns depends on whether they are FK targets:**

- **Not a FK target, nullable (or has a default)**: stop populating it. Leave the column in the schema but don't write to it on JIT.
- **Not a FK target, NOT NULL with no default**: populate it from `sessionClaims` **once during the JIT insert only** to satisfy the constraint. Do not re-sync on subsequent requests — Clerk remains the source of truth, the local column is just frozen at first-insert.
- **Is a FK target** (other tables reference `usersTable.email`, `usersTable.username`, etc.): **keep populating it** from `sessionClaims` during JIT upsert. The value is available in the session token — just write it through. Do not refactor FKs or change the schema. Keep changes minimal.

### 3. Audit every client API call path

Search for any API calls that use direct `fetch()` instead of `apiRequest`/`getQueryFn` from `@lib/queryClient`. Inventory them before migration, then switch each one to the canonical path during frontend migration. A hand-written `fetch()` can easily omit cookies or bypass error handling in `queryClient.ts`; the fix is the canonical cookie-based path, not bearer-token auth.

## Server-Side Migration

### 1. Remove auth routes

Delete the auth routes file (typically `server/replit_integrations/auth/routes.ts`) and the call to `registerAuthRoutes(app)` in `server/index.ts` (or wherever the Express app is wired up). This removes:

- `GET /api/login` — OIDC redirect with PKCE
- `GET /api/callback` — token exchange + user upsert + session creation
- `GET /api/logout` — session clear + OIDC end-session redirect
- `GET /api/auth/user` — returns user from session
- `POST /api/mobile-auth/token-exchange` — mobile PKCE flow (if present)
- `POST /api/mobile-auth/logout` — mobile session delete (if present)

### 2. Remove session library

Delete `server/replit_integrations/auth/replitAuth.ts`. This contains `ISSUER_URL`, `getOidcConfig()`, `getSession()`, the `express-session` + `connect-pg-simple` setup, `passport` strategy registration, and the OIDC login/callback/logout handlers. Clerk manages sessions externally.

Also remove `server/replit_integrations/auth/storage.ts` (the `authStorage.upsertUser()` helper) and the barrel `server/replit_integrations/auth/index.ts`. After deleting the files, remove the `server/replit_integrations/auth/` directory if it is empty.

### 3. Remove auth middleware

Remove the `await setupAuth(app);` and `registerAuthRoutes(app);` calls and the `import { setupAuth, registerAuthRoutes } from "./replit_integrations/auth"` in `server/index.ts`. The legacy integration uses `passport.initialize()` / `passport.session()` and `express-session` — all of that goes away with Clerk.

Also delete any `import { isAuthenticated } from "./replit_integrations/auth"` (or relative-path equivalents) at the top of individual route handler files (e.g. `server/routes/*.ts`). After step 2 deletes the auth module, those imports point at a removed path and will break the build. Step 6 below describes the Clerk replacement pattern.

### 4. Remove `upsertUser` — replace with JIT provisioning

**Skip this step if the original app deliberately did not auto-create user rows on login** (i.e., the users table is curated and `upsertUser` was absent or gated by an allowlist check). Introducing JIT in that case silently breaks authorization. Instead, leave the existing gate intact: `requireAuth` should look up the user via the bridge column, return 401/403 when no row exists, and let the frontend render that as a terminal access-denied state (see step 7).

Remove the existing Replit Auth `upsertUser` logic that inserts/updates identity data in the local `users` table on each OIDC callback — Clerk now owns identity data.

**Replace it with just-in-time (JIT) provisioning** that uses the **same bridge column** the app already uses. Add a middleware (or logic within `requireAuth`) that runs after Clerk session validation.

The example below uses the Replit Auth subject ID bridge (blueprint default: old `upsertUser` set `users.id = claims.sub`, and Clerk exposes that migrated value as `sessionClaims.userId`). **You MUST adapt the query column, session claim, and insert values to match the bridge field you found in the app** — for example, email, username, or a separate app UUID lookup. If your bridge field was NOT id then DO NOT use id for the lookup.

```typescript
import { eq } from "drizzle-orm";
import { db } from "../db";
import { users } from "@shared/schema";

// This sample uses the Replit Auth user ID bridge.
// Replace users.id/userId with the app's real bridge field if it uses email,
// username, or another local user identifier.
const userId = auth.sessionClaims?.userId || auth.userId;

let [dbUser] = await db.select().from(users).where(eq(users.id, userId)).limit(1);

if (!dbUser) {
  const [inserted] = await db
    .insert(users)
    .values({ id: userId })
    .onConflictDoNothing()
    .returning();
  if (inserted) {
    dbUser = inserted;
  } else {
    [dbUser] = await db.select().from(users).where(eq(users.id, userId)).limit(1);
  }
}

req.dbUser = dbUser;
```

For migrated users on the ID bridge, `sessionClaims.userId` returns their original Replit Auth subject ID (stored as `externalId` in Clerk), so their existing row is found immediately. New users get the Clerk native ID (e.g., `user_2abc...`) as their `users.id`. For any other bridge field, use the corresponding value from `sessionClaims` — no Clerk API call is needed in the request path.

**General rules for all bridge types:**

- `users.id` is NOT guaranteed to be a Replit Auth or Clerk user ID; it can be a random UUID. Verify that each bridge field is actually available in Replit Auth/Clerk session claims.
- The `values` object should include safe defaults for any required app columns (e.g., `role: "viewer"`, `permissions: []`, `is_active: true`). The exact defaults depend on the app's schema.
- This is safe because Clerk's `clerkMiddleware()` has already cryptographically verified the session token before this code runs — the user identity is not user-supplied input.
- `onConflictDoNothing` handles race conditions from concurrent first-requests.
- **Do NOT call `clerkClient.users.getUser()` in the middleware.** Everything needed for the bridge is already in `sessionClaims`.

### 5. Wire Clerk server middleware

Follow the rest of the `clerk-auth` skill and `.local/skills/clerk-auth/references/setup-and-customization.md` to:

- Copy the proxy middleware template and mount it **before body parsers** (the proxy streams raw bytes — mounting after body parsers breaks it)
- Mount `clerkMiddleware()` with `publishableKeyFromHost` for custom-domain support
- Create `requireAuth` middleware that rejects unauthenticated requests, resolves the local user via the bridge column (step 4), and sets `req.dbUser`

### 6. Transition `req.isAuthenticated()` / `req.user` in route handlers

Search all route files and replace:

| Remove (Replit Auth) | Replace with (Clerk) |
| --- | --- |
| `req.isAuthenticated()` guard | `requireAuth` middleware (rejects unauthorized requests automatically) |
| `req.user.claims.sub` or `req.user.id` | `req.dbUser.id` |
| Identity field reads (`req.user.email`, `authStorage.getUser(...)`) | `auth.sessionClaims.email`, `auth.sessionClaims.firstName`, etc. (from JWT — no API call) |
| `req.user.role`, `req.user.permissions`, or any app-column read | `req.dbUser.role`, `req.dbUser.permissions` — still from local DB |
| `import { isAuthenticated } from "./replit_integrations/auth"` | `import { requireAuth } from "<your-middlewares>"` (per the `clerk-auth` skill) |

Key principle: **swap the identity provider, keep the same app structure.** Route handlers that check roles, permissions, or other app-specific fields continue to read them from the local `users` table via `req.dbUser`. The only change is where identity data (email, name, avatar) comes from — Clerk instead of the local DB.

### 7. Frontend auth state and the 401 edge cases

Two kinds of 401 produce the same loop / spinner symptom but need different fixes — handle both.

**Transient 401 — Clerk hasn't loaded yet.** Calls that fire on mount, before Clerk has validated its session cookie, return 401 even for a valid signed-in user. Best fix: use Clerk's hooks directly (they gate themselves) and delete any custom auth context that fetches identity on mount (see Frontend Migration step 1). If a custom context must stay, gate every server call on `isLoaded`, skip when signed out, and derive the loading flag from `isLoaded`:

```typescript
const { isLoaded, isSignedIn } = useAuth();

useEffect(() => {
  if (!isLoaded || !isSignedIn) return;
  checkAuth();
}, [isLoaded, isSignedIn]);
```

**Permanent 401 — Clerk authenticates, server rejects** (no local row, deactivated, role denied). **Do NOT redirect to `/sign-in`** — the user is already signed in at Clerk and will bounce back, creating an infinite loop. Model three states:

- **Not signed in** → redirect to `/sign-in`
- **Signed in, server returns 401/403** → terminal access-denied page (no redirect)
- **Signed in, server returns 200** → render the app

This third state is mandatory whenever the server can reject a Clerk-authenticated user — i.e., always, but especially when § 4's JIT step was skipped.

### 8. Transition dependencies

Follow the `clerk-auth` skill setup section to install Clerk server dependencies. Then remove Replit Auth dependencies:

```bash
npm uninstall openid-client passport express-session connect-pg-simple memoizee @types/passport @types/express-session @types/connect-pg-simple @types/memoizee
```

## Frontend Migration

### 1. Remove the Replit Auth hook

Delete `client/src/hooks/use-auth.ts` and `client/src/lib/auth-utils.ts`. The `useAuth()` hook in that file called `GET /api/auth/user` and provided `{ user, isLoading, isAuthenticated, logout }`. Remove all imports of it from the client (usually `import { useAuth } from "@/hooks/use-auth"` or `"./hooks/use-auth"`).

**If the app has a custom auth context (`AuthContext`, `UserProvider`, `AuthProvider`, etc.) that fetches `/api/auth/user` on mount, remove the entire layer — not just the hook it imports.** Clerk's `useUser()` / `useAuth()` already expose identity with no server roundtrip, and any context that re-fetches it on mount races with Clerk's session loading and produces the transient-401 loop (see Troubleshooting). Replace consumers with Clerk's hooks directly. If the context must stay because it overlays app-specific state on top of Clerk's user, see step 7 for the required `isLoaded` gating.


### 2. Transition auth hook calls

| Remove (Replit Auth) | Replace with (Clerk — see `clerk-auth` skill) |
| --- | --- |
| `useAuth()` from `@/hooks/use-auth` | `useUser()` + `useAuth()` from `@clerk/react` |
| `user.email` | `user?.primaryEmailAddress?.emailAddress` |
| `user.profileImageUrl` | `user?.imageUrl` |
| `isUnauthorizedError(err)` + `redirectToLogin()` | Clerk `<SignIn>` route / `useClerk().redirectToSignIn()` |
| `logoutMutation.mutate()` (hits `/api/logout`) | `signOut()` from `useClerk()` |
| `isAuthenticated` conditional rendering | `<Show when="signed-in">` / `<Show when="signed-out">` |

### 3. Replace logout handlers

Search all client code for `/api/logout`, `logout()`, `logoutMutation`, `redirect("/api/logout")`, logout buttons, account menus, and settings-page logout handlers.

Replit Auth web logout hit the server route (`GET /api/logout`) because the app owned the session cookie. Clerk web logout is client-only: replace every logout handler with `signOut()` from `useClerk()`. Do **not** keep, call, or recreate `/api/logout` for web logout.

```typescript
import { useClerk } from "@clerk/react";

function LogoutButton() {
  const { signOut } = useClerk();

  return <button onClick={() => signOut({ redirectUrl: "/" })}>Log out</button>;
}
```

### 4. User ID in frontend comparisons

Anywhere the frontend compares user IDs against app data (e.g., `post.authorId === user.id`):

```typescript
const { user } = useUser();
const userId = user?.externalId ?? user?.id;
// externalId = original Replit Auth ID for migrated users
// id = Clerk native ID for new users
```

### 5. Wire Clerk frontend

Follow the rest of the `clerk-auth` skill and `.local/skills/clerk-auth/references/setup-and-customization.md` to install client dependencies and set up `ClerkProvider` with Wouter routing, `/sign-in` and `/sign-up` routes, and `ClerkQueryClientCacheInvalidator` if using `@tanstack/react-query`. **Copy `clerkPubKey`, `clerkProxyUrl`, the `<ClerkProvider>` props, and the `/sign-in/*?` / `/sign-up/*?` route paths verbatim** — these are the most common places agents drift and silently break dev or prod. The setup reference also contains critical patterns for the full `path` prop with base prefix and the `stripBase` helper — both required to avoid 404s.

After removing the deleted files' imports and running `npm install` (no workspace package to remove on the legacy stack — the hook lived directly in `client/src/hooks/use-auth.ts`), verify the client builds with no dangling references.

## Troubleshooting

### Web 401 does not mean web token auth

For web apps, a 401 is a cookie/session loading, middleware, local-user bridge, or authorization problem. Web auth uses Clerk session cookies; mobile/Expo auth uses bearer tokens because mobile has no browser cookie jar. Do not add `getToken()`, `setAuthTokenGetter`, or `Authorization: Bearer` to browser requests — those token patterns are only for Expo/mobile clients.

### CSP blocks Clerk or Cloudflare Turnstile

Only relevant if the app manually configures a Content Security Policy (e.g., via Helmet). Most apps don't — skip this if there's no CSP configuration.

If the app does have a CSP and sign-in silently fails or shows a CAPTCHA error after migration:

- Add Clerk domains to `script-src`, `connect-src`, and `frame-src`
- Add `challenges.cloudflare.com` to the same directives (Clerk uses Cloudflare Turnstile for bot protection)
- CSP only allows wildcards at the leftmost label — `*.replit.dev` is valid but `clerk.*.replit.dev` is silently ignored

### Infinite redirect loop after migration

Two root causes produce the same symptom — diagnose which before fixing.

**A. Race with Clerk session loading (transient 401).** A custom auth context fetches `/api/auth/user` on mount before Clerk has attached its session cookie; the 401 redirects to `/sign-in`; Clerk finishes loading and bounces back. Tells: `/api/auth/user` returns 401 once then 200 for the same session, and the app's loading flag comes from `useState(true)` rather than Clerk's `isLoaded`. Fix per § 7 (Transient 401) — preferably delete the custom context and use Clerk's hooks directly.

**B. Two-state UI on a permanent 401.** The frontend only models "authenticated / not", and the server keeps returning 401 (no local row, role denied, user deactivated). Common when § 4's JIT step was skipped because the app uses a curated users table. Tells: `/api/auth/user` returns 401 on every retry with `isLoaded === true` and `isSignedIn === true`. Fix per § 7 (Permanent 401) — add the third "access denied" state and route to a terminal error page.
