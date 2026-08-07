# Clerk Auth — Setup and Customization

Set up Clerk authentication with proxy support. Keys are automatically provisioned.

## Setup

### Step 1: Provision Clerk App

Use the `codeExecution` tool to call `setupClerkWhitelabelAuth` to provision your Clerk app and set secrets:

```javascript
const result = await setupClerkWhitelabelAuth();
console.log(result);
```

### Step 2: Copy Proxy Middleware Template

```bash
mkdir -p server/middlewares
cp .local/skills/clerk-auth/templates/api-server/src/middlewares/clerkProxyMiddleware.ts server/middlewares/clerkProxyMiddleware.ts
```

### Step 3: Install Server Dependencies

```bash
npm install http-proxy-middleware @clerk/express @clerk/shared cors
npm install --save-dev @types/cors
```

### Step 4: Wire Up the Express App

In `server/index.ts` (or wherever the Express app is constructed), mount the proxy middleware before body parsers (the proxy streams raw bytes). If the existing file already mounts `express.json({ verify: ... })` (e.g. to capture `req.rawBody` for webhook signature verification), keep that intact — mount `clerkMiddleware()` alongside it, don't replace it.

```typescript
import express from "express";
import cors from "cors";
import { clerkMiddleware } from "@clerk/express";
import { publishableKeyFromHost } from "@clerk/shared/keys";
import {
  CLERK_PROXY_PATH,
  clerkProxyMiddleware,
  getClerkProxyHost,
} from "./middlewares/clerkProxyMiddleware";

const app = express();

app.use(CLERK_PROXY_PATH, clerkProxyMiddleware());

app.use(cors({ credentials: true, origin: true }));
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Resolve the publishable key from the incoming request host so the same
// server can serve multiple Clerk custom domains. Falls back to
// CLERK_PUBLISHABLE_KEY when the host doesn't map to a custom domain.
//
// getClerkProxyHost is shared with clerkProxyMiddleware so that both
// halves of the auth setup agree on which hostname is canonical.
app.use(
  clerkMiddleware((req) => ({
    publishableKey: publishableKeyFromHost(
      getClerkProxyHost(req) ?? "",
      process.env.CLERK_PUBLISHABLE_KEY,
    ),
  })),
);

// ...existing route registration...
```

On the legacy fullstack stack, the proxy middleware must be mounted before any body parsers and before the existing route registration calls (e.g. `registerRoutes(app)`).

### Step 5: Install Client Dependencies

```bash
npm install @clerk/react
```



## IMPORTANT

- The server-side proxy code is production only and is not used in development. Do not ask for or set any env vars related to the proxy. All production setup is handled by a separate system.
- When delegating to the design subagent, be sure to include all of the code instructions/guidance below in the task description so it follows them closely
- Always customize sign-in/sign-up pages to match the site's theme — generate a branded logo, build the appearance object, and set localization. Users should never land on a default unstyled Clerk page.
- **Copy the canonical wiring (`clerkPubKey`, `clerkProxyUrl`, `<ClerkProvider>` props, server `clerkMiddleware` block, sign-in/sign-up `<Route>` paths) verbatim.** The same code is meant to run in dev and prod — env vars are empty in dev, auto-populated in prod. Do NOT add `PROD` / `NODE_ENV` gates or substitute look-alike code from prior Clerk knowledge. Only theme/UI is yours to modify.

## Home Route Behavior

The artifact's base path (`import.meta.env.BASE_URL`) must always be a publicly accessible landing page for unauthenticated users — never redirect them to sign-in or sign-up. Dropping users onto a sign-in screen with no context about the app causes confusion and hurts conversion. Avoid `<RedirectToSignIn>`, wrapping the homepage in auth-only gates, or any explicit redirect from the base path to `/sign-in` or `/sign-up`.

For authenticated users, always redirect the base path to a user-portal view so they land directly in the app without an extra click. After the user signed-out, redirects to the home route rather than the sign-in route.

Example routing with redirect logic:

```typescript
import { Show } from "@clerk/react";
import { Switch, Route, Redirect } from "wouter";

// Inside <WouterRouter base={basePath}>, all route paths and navigation
// targets are base-relative. "/" matches {basePath}/, "/user-portal"
// navigates to {basePath}/user-portal, etc.

function HomeRedirect() {
  return (
    <>
      <Show when="signed-in">
        <Redirect to="/user-portal" />
      </Show>
      <Show when="signed-out">
        <Home />
      </Show>
    </>
  );
}

function UserPortal() {
  return (
    <>
      <Show when="signed-in">
        <UserPortalPage />
      </Show>
      <Show when="signed-out">
        <Redirect to="/" />
      </Show>
    </>
  );
}

function Router() {
  return (
    <Switch>
      <Route path="/" component={HomeRedirect} />
      <Route path="/user-portal" component={UserPortal} />
      {/* Other routes */}
    </Switch>
  );
}
```

## After Setup - Web App

### Auth transport while building

For the web app, Clerk auth is cookie-based. Do not add `getToken()`, `setAuthTokenGetter`, `Authorization: Bearer`, or any other explicit token handling to browser API calls. Clerk's browser SDK and Express middleware use the session cookie.

A 401 from the web app does not mean the web app needs token auth. Debug cookies/session loading, middleware ordering, `requireAuth`, the local-user bridge/JIT provisioning, or authorization state instead. Token handling belongs only in the Expo/mobile section below, where there is no browser cookie jar.

### 1. Set up client routing with Wouter base path

**This is vital.** Setting `<WouterRouter base={basePath}>` makes every location change via wouter's components and hooks (e.g. `<Route>`, `<Redirect to>`, `setLocation`) relative to the base URL. However, Clerk's `<SignIn path>` and `<SignUp path>` props read `window.location.pathname` directly and must be **full** paths — use `` `${basePath}/sign-in` `` and `` `${basePath}/sign-up` ``.

**Important:** The proxy setup does not work with Clerk's hosted pages. You must create dedicated `/sign-in` and `/sign-up` routes in your app to handle OAuth callbacks. Link to these pages from your landing page CTAs (e.g. "Sign In" / "Sign Up" buttons that navigate to `/sign-in` and `/sign-up`).

**Critical routing requirements** (getting either of these wrong causes 404s or broken OAuth):

1. **Routes MUST be exactly `path="/sign-in/*?"` and `path="/sign-up/*?"`** — character-for-character. The `/*?` optional wildcard is the only wouter syntax that matches both the bare URL and Clerk's OAuth sub-paths (`/sign-in/sso-callback`, `/sign-in/factor-one`). Do not substitute `/sign-in`, `/sign-in/*`, or wouter's named-param syntax (`/sign-in/:rest*`).
2. **`<SignIn>` and `<SignUp>` MUST have `routing="path"` and a full `path` prop.** Clerk reads `window.location.pathname` directly, so the `path` must include the base path prefix: `path={`${basePath}/sign-in`}`. Without this, Clerk can't match its internal routes and renders nothing or errors.

### Customizing Sign-In / Sign-Up Pages
1. **Install themes package**: `npm install @clerk/themes`.
2. **Branded SVG logo** → `public/logo.svg`. REQUIRED. `logoImageUrl` absolute: `` `${window.location.origin}${basePath}/logo.svg` ``.
3. **Match the site's font** — set `fontFamily` in `variables` to the same font the rest of the app uses. If the app loads a custom Google Font or local font via CSS, use that same family name so the Clerk UI feels native to the site.
4. **Global CSS setup** — the steps below assume Tailwind v4 with the `@tailwindcss/vite` plugin. **If the project uses Tailwind 3 / PostCSS** (typical on legacy Fullstack JS projects), keep the existing `@tailwind base; @tailwind components; @tailwind utilities;` directives, drop the `cssLayerName: "clerk"` setting, and skip step 5 below — it only applies to Tailwind v4. Import the shadcn theme via the JS object only.

   On Tailwind v4, the layer declaration must come before `@import 'tailwindcss'`:

   ```css
   @layer theme, base, clerk, components, utilities;
   @import 'tailwindcss';
   @import '@clerk/themes/shadcn.css'; /* only if using shadcn theme */
   ```

5. **Disable lightningcss optimization in `vite.config.ts`** (Tailwind v4 only) by passing `tailwindcss({ optimize: false })` to the `@tailwindcss/vite` plugin. Without this, nested `@layer` imports from `@clerk/themes/*.css` get reordered in prod builds and Clerk UI renders correctly in dev but broken in prod.

6. Build `appearance` (see code block in the App.tsx example) and pass it + `localization` to `<ClerkProvider>`.

Rules:

- **Themes are imports, not strings.** `import { shadcn } from '@clerk/themes'` then `theme: shadcn`. The only string value is `theme: 'simple'`.
- **Logo/layout props go in `options`**, not `layout`: `logoPlacement`, `logoLinkUrl`, `logoImageUrl`, `socialButtonsPlacement`, `socialButtonsVariant`.
- **Colors go in `variables`, not `elements`.** Current names: `colorPrimary`, `colorForeground`, `colorMutedForeground`, `colorBackground`, `colorInput`, `colorInputForeground`, `colorDanger`, `colorNeutral`. Do **not** use the deprecated names (`colorText`, `colorTextSecondary`, `colorInputBackground`, `colorInputText`) — they silently no-op.
- **Text contrast.** Every text-bearing element (`headerTitle`, `headerSubtitle`, `socialButtonsBlockButtonText`, `formFieldLabel`, `footerActionLink`, `footerActionText`, `dividerText`, etc.) must have strong contrast against its background. Fill in all `"..."` placeholders in the `elements` block — don't skip any.
- **`elements`** accepts Tailwind classes (with `cssLayerName` set) or inline CSS objects. Find keys by inspecting the DOM — any `cl-*` class before the lock icon is stable; drop the `cl-` prefix for the key.
- **Pseudo-states** (`:hover`, `:focus`, `::placeholder`) need a stylesheet targeting `cl-*` classes outside any `@layer`. Inline style objects can't express them. Avoid `@apply` in that stylesheet on Tailwind v4 — use raw values or CSS variables.

Pitfalls:

- **Card background transparent** — `card` and `footer` are intentionally `!bg-transparent` so `cardBox` owns the single surface. If the card is see-through, `cardBox` is missing a background — fill in its `"..."` with a bg color or Tailwind class.
- **Placeholder text invisible on dark bg** — add `.cl-formFieldInput::placeholder { color: ...; opacity: 1; }` in a stylesheet.
- **Card too narrow or too wide** — Always set an explicit width on `cardBox` (e.g. `w-[440px] max-w-full`) — never rely on `w-full` alone.
- **Clerk UI looks correct in dev but broken in prod** — set `tailwindcss({ optimize: false })` in `vite.config.ts` (see step 5 above).
- **`publishableKey` must be `publishableKeyFromHost(window.location.hostname, import.meta.env.VITE_CLERK_PUBLISHABLE_KEY)` from `@clerk/react/internal`** — never the raw env var, never `undefined`, never `window.location.host` (includes the dev port), and never `publishableKeyFromHost(...) || env` (the helper always returns a key, so the fallback never runs).
- **`proxyUrl={clerkProxyUrl}` is unconditional**, with `clerkProxyUrl = import.meta.env.VITE_CLERK_PROXY_URL`. The env var is empty in dev (intentional) and auto-populated in prod. Do not gate it on `PROD` / `NODE_ENV`, do not hardcode `/api/__clerk`, do not omit the prop — any of these breaks the prod proxy.


```typescript
import { useEffect, useRef } from "react";
import { ClerkProvider, SignIn, SignUp, Show, useClerk } from '@clerk/react';
import { publishableKeyFromHost } from '@clerk/react/internal';
import { shadcn } from '@clerk/themes'; // or `dark`, `neobrutalism`, `shadesOfPurple`
import { Switch, Route, useLocation, Router as WouterRouter } from 'wouter';
import { queryClient } from "./lib/queryClient";
import { QueryClientProvider, useQueryClient } from "@tanstack/react-query";

// REQUIRED — copy verbatim. Resolves the key from window.location.hostname so the
// same build serves multiple Clerk custom domains. Do not inline the env var, leave
// publishableKey undefined, or replace publishableKeyFromHost with anything else.
const clerkPubKey = publishableKeyFromHost(
  window.location.hostname,
  import.meta.env.VITE_CLERK_PUBLISHABLE_KEY,
);

// REQUIRED — copy verbatim. Empty in dev (Clerk hits dev FAPI directly), auto-set
// in prod. Do NOT gate on import.meta.env.PROD / NODE_ENV — the empty dev value
// is intentional, and any branching breaks the prod proxy.
const clerkProxyUrl = import.meta.env.VITE_CLERK_PROXY_URL;

const basePath = import.meta.env.BASE_URL.replace(/\/$/, "");

// Clerk passes full paths to routerPush/routerReplace, but wouter's
// setLocation prepends the base — strip it to avoid doubling.
function stripBase(path: string): string {
  return basePath && path.startsWith(basePath)
    ? path.slice(basePath.length) || "/"
    : path;
}

if (!clerkPubKey) {
  throw new Error('Missing VITE_CLERK_PUBLISHABLE_KEY in .env file');
}

const clerkAppearance = {
  theme: shadcn, // imported object from @clerk/themes; not a string
  cssLayerName: "clerk",
  options: {
    logoPlacement: "inside" as const,
    logoLinkUrl: basePath || "/",
    logoImageUrl: `${window.location.origin}${basePath}/logo.svg`,
  },
  variables: {
    colorPrimary: "...",
    colorForeground: "...",       // body text
    colorMutedForeground: "...",  // subtitles, helper text, divider "or", footerActionText
    colorDanger: "...",
    colorBackground: "...",       // card background
    colorInput: "...",            // input background
    colorInputForeground: "...",  // input text
    colorNeutral: "...",          // borders
    fontFamily: "...",
    borderRadius: "...",
  },
  elements: {
    rootBox: "w-full flex justify-center",
    // CRITICAL — cardBox must include a background color (e.g. bg-white). card/footer are !bg-transparent so cardBox is the only surface.
    cardBox: "bg-... rounded-2xl w-[440px] max-w-full overflow-hidden",
    card: "!shadow-none !border-0 !bg-transparent !rounded-none",
    footer: "!shadow-none !border-0 !bg-transparent !rounded-none",
    // Text-bearing elements — Tailwind classes or inline style objects both work (with cssLayerName set):
    headerTitle: "...",
    headerSubtitle: "...",
    socialButtonsBlockButtonText: "...",
    formFieldLabel: "...",
    footerActionLink: "...",
    footerActionText: "...",
    dividerText: "...",
    identityPreviewEditButton: "...",
    formFieldSuccessText: "...",
    alertText: "...",
    // Non-text elements:
    logoBox: "...",
    logoImage: "...",
    socialButtonsBlockButton: "...",
    formButtonPrimary: "...",
    formFieldInput: "...",
    footerAction: "...",
    dividerLine: "...",
    alert: "...",
    otpCodeFieldInput: "...",
    formFieldRow: "...",
    main: "...",
  },
};

function SignInPage() {
  return (
    <div className="flex min-h-[100dvh] items-center justify-center bg-background px-4">
      {/* path must be the full browser path — Clerk reads window.location.pathname directly */}
      <SignIn routing="path" path={`${basePath}/sign-in`} signUpUrl={`${basePath}/sign-up`} />
    </div>
  );
}

function SignUpPage() {
  return (
    <div className="flex min-h-[100dvh] items-center justify-center bg-background px-4">
      <SignUp routing="path" path={`${basePath}/sign-up`} signInUrl={`${basePath}/sign-in`} />
    </div>
  );
}

function LogoutButton() {
  const { signOut } = useClerk();

  return (
    <button type="button" onClick={() => signOut({ redirectUrl: basePath || "/" })}>
      Log out
    </button>
  );
}

// Helps user's webview stay up-to-date when the signed-in user changes by invalidating the QueryClient cache.
function ClerkQueryClientCacheInvalidator() {
  const { addListener } = useClerk();
  const queryClient = useQueryClient();
  const prevUserIdRef = useRef<string | null | undefined>(undefined);

  useEffect(() => {
    const unsubscribe = addListener(({ user }) => {
      const userId = user?.id ?? null;
      if (
        prevUserIdRef.current !== undefined &&
        prevUserIdRef.current !== userId
      ) {
        queryClient.clear();
      }
      prevUserIdRef.current = userId;
    });
    return unsubscribe;
  }, [addListener, queryClient]);

  return null;
}

function ClerkProviderWithRoutes() {
  const [, setLocation] = useLocation();

  return (
    <ClerkProvider
      publishableKey={clerkPubKey}
      proxyUrl={clerkProxyUrl}
      appearance={clerkAppearance}
      signInUrl={`${basePath}/sign-in`}
      signUpUrl={`${basePath}/sign-up`}
      localization={{
        signIn: {
          start: {
            title: "Welcome back",
            subtitle: "Sign in to access your account",
          },
        },
        signUp: {
          start: {
            title: "Create your account",
            subtitle: "Get started today",
          },
        },
      }}
      routerPush={(to) => setLocation(stripBase(to))}
      routerReplace={(to) => setLocation(stripBase(to), { replace: true })}
    >
      <QueryClientProvider client={queryClient}>
        <ClerkQueryClientCacheInvalidator />
        <Switch>
          {/* HomeRedirect renders homepage or user portal based on signed-in status. */}
          <Route path="/" component={HomeRedirect} />
          {/* REQUIRED — copy "/sign-in/*?" and "/sign-up/*?" verbatim. The /*? optional
              wildcard is the only wouter syntax that matches both the bare URL and Clerk's
              OAuth sub-paths. Not /sign-in, not /sign-in/*, not /sign-in/:rest*. */}
          <Route path="/sign-in/*?" component={SignInPage} />
          <Route path="/sign-up/*?" component={SignUpPage} />
          {/* Add other routes here */}
        </Switch>
      </QueryClientProvider>
    </ClerkProvider>
  );
}

function App() {
  return (
    <WouterRouter base={basePath}>
      <ClerkProviderWithRoutes />
    </WouterRouter>
  );
}

export default App;
```


### 2. Protect API routes

Use `getAuth` from `@clerk/express` to check for an authenticated user:

```typescript
import { getAuth } from "@clerk/express";

const requireAuth = (req: any, res: any, next: any) => {
  const auth = getAuth(req);
  const userId = auth?.sessionClaims?.userId || auth?.userId;
  if (!userId) {
    return res.status(401).json({ error: "Unauthorized" });
  }
  req.userId = userId;
  next();
};

app.get("/api/protected", requireAuth, handler);
```

### 3. Use auth state in components

Use the `<Show>` component to conditionally render based on authentication state:

```typescript
import { Show } from "@clerk/react";

function MyComponent() {
  return (
    <>
      {/* Show content only to signed-in users */}
      <Show when="signed-in">
        {/* Protected content */}
      </Show>

      {/* Show content only to signed-out users */}
      <Show when="signed-out">
        {/* Login prompt or redirect */}
      </Show>
    </>
  );
}
```

For web logout, call Clerk's client SDK directly with `signOut()` from `useClerk()`. Do not keep or recreate `/api/logout`, and do not route logout buttons through the Express API — Clerk owns the browser session.

### 4. Render user profile

Use `useUser` hook to get current authenticated user.
**Important:** Do not use `<UserButton />` by default — the built-in component is not customizable and may expose confusing Clerk-level user management options to end users.

```typescript
import { useUser } from "@clerk/react";

// Render component with user profile
const { user, isLoaded } = useUser();
```



## Environment Variables (Auto-Provisioned)

These are set automatically by `setupClerkWhitelabelAuth()`. Do not ask the user for these values.

- `CLERK_SECRET_KEY` (secret): Auto-provisioned secret key
- `CLERK_PUBLISHABLE_KEY` (secret): Auto-provisioned publishable key
- `VITE_CLERK_PUBLISHABLE_KEY` (secret): Auto-provisioned publishable key

## Migrating from Replit Auth

When migrating an existing app from Replit Auth to Clerk, read the following references:

- `references/web-migration.md` — Web app migration (Express API server + React+Vite frontend): what to remove and what to transition.

## Troubleshooting

### Unauthorized (401) errors in the preview web app

When API requests from the web app return 401 Unauthorized, first check which platform you are debugging:

- **Web app:** auth uses Clerk session cookies. Do not add `getToken()`, `setAuthTokenGetter`, `Authorization: Bearer`, or any other explicit token handling to browser requests.
- **Mobile/Expo app:** auth uses bearer tokens because there is no browser cookie jar. `setAuthTokenGetter` belongs here, not in web code.

For web 401s, adding mobile-style token auth is the wrong fix. The browser should send Clerk session cookies with same-origin API requests, so debug cookie/session loading, middleware, and local authorization instead.

Instead:

1. **Check middleware setup** — Verify that `clerkMiddleware()` is mounted in `server/index.ts` before the API routes, and that the `requireAuth` middleware is correctly wired on protected endpoints (checking `getAuth(req)` for a valid session).
2. **When not sure, add debugging logs** — Add temporary logging inside the `requireAuth` middleware (e.g. log the output of `getAuth(req)`) to see what Clerk is receiving. Then restart the client and API server workflows and ask the user to test again so you can inspect the logs.

## Limitations

- Idempotent: Safe to call multiple times
- Proxy path is hardcoded to `/api/__clerk`
