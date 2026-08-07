# Add a mobile (Expo) companion app

## Goal

The user just imported a web app and the migration to the Replit `pnpm_workspace` stack has finished. Add a **new Expo mobile artifact** that mirrors the web app's data layer.

This task starts AFTER the migration task is merged. The migration may have landed in one of two shapes — see Step 1 below — so your first job is to detect which mode this is and mirror what the web app actually uses. The web artifact must stay untouched.

## In scope

- Detect the web artifact created by the migration task and read enough of it to understand the app's screens, state, and API usage.
- Create a new Expo artifact via `createArtifact({ artifactType: "expo", slug: "<web-slug>-mobile", previewPath: "/", title: "<Title> Mobile", description: "<short paragraph: what the app is, what it does, and who it is for>" })`.
- Translate the web app's screens / flows into a native mobile UX using the `expo` and `mobile-ui` skills. Aim for a mobile-native feel, not a phone-shaped copy of the website.
- **(Mode A)** Reuse the existing API client (`@workspace/api-client-react`) — the same generated hooks the web app uses. **(Mode B)** Mirror the web app's actual data layer (exported fetch helper or third-party SDK).
- Wire up `setBaseUrl` in `app/_layout.tsx` so requests target the deployed API.
- Configure `app.json` with a sensible `name`, `slug`, and `bundleIdentifier` derived from the existing web app's name.
- **(Mode A) Additive backend / shared-lib changes when mobile parity needs them.** It is OK to add new endpoints to `artifacts/api-server/`, new fields to `lib/api-spec/openapi.yaml` (and regenerate `lib/api-client-react/`), or a new column to `lib/db/` schema for mobile-specific concerns (push tokens, device registration, mobile-only resources). Constraint: **purely additive**. Do not change or remove existing endpoints, fields, or columns the web app depends on; do not break the web app's existing contract. If the change cannot be additive, propose a follow-up task instead.

## Out of scope

- **Do not modify the web artifact (`artifacts/<web-slug>/`).** It is the user's product; leave it untouched.
- **Do not change existing backend behavior.** Additive endpoints / fields are OK (see "In scope"); changing or removing existing ones is not.
- New product features the web app doesn't have, beyond the mobile-specific plumbing called out above. The companion is a mirror, not an expansion.
- Strict typecheck — use `// @ts-ignore` to keep moving. Functional + visual parity matters more than zero TS errors.

## Pre-existing state (read, don't relitigate)

After the migration task merged, the workspace always contains:

- `artifacts/<web-slug>/` — the web artifact ported from the original import. Read this to understand screens, flows, and API usage.

In **Mode A** the workspace also contains:

- `artifacts/api-server/` — backend (Express + Drizzle).
- `lib/api-spec/openapi.yaml` — API contract.
- `lib/api-client-react/src/generated/` — generated React Query hooks. Reuse these in the Expo app via `@workspace/api-client-react`.
- `lib/db/` — Drizzle schema + client.

In **Mode B** (frontend-only or legacy fetch) none or some of those `lib/*` and `artifacts/api-server/` paths may be missing — work with what's actually there.

You are adding a sibling under `artifacts/`, nothing else.

## User communication

Tell the user what's happening at each major phase. Keep it short and non-technical:

- Before starting: "Looking at your web app to plan the mobile version..."
- Before creating the artifact: "Setting up your mobile app scaffold..."
- Before screen porting: "Building the mobile screens..."
- Before wiring up the API: "Connecting the mobile app to your existing backend..."
- Before `markTaskComplete`: "Running checks to make sure the mobile app builds and renders. This may take a minute."

## Steps

1. **Detect what the migration produced**

   The migration recipes can land in one of two shapes. Before reading skills, in one parallel batch:

   - `ls artifacts/` — confirm what artifact kinds exist.
   - `cat artifacts/<web-slug>/package.json` and search the web artifact for imports of `@workspace/api-client-react`.
   - `ls lib/` and check for `lib/api-spec/openapi.yaml` + `lib/api-client-react/`.

   This puts the companion in one of two modes:

   - **Mode A — backend + codegen present.** `artifacts/api-server/` exists, `lib/api-spec/openapi.yaml` is populated, and the web artifact imports `@workspace/api-client-react`. The mobile app reuses the same generated hooks and the same backend.
   - **Mode B — frontend-only or legacy fetch.** Either `artifacts/api-server/` does not exist (frontend-only import), OR it exists but the web app calls a hand-written fetch layer / third-party services directly without `@workspace/api-client-react`. In this mode:
     - **Do not invent an `artifacts/api-server/`** if one doesn't exist.
     - **Do not introduce `@workspace/api-client-react`** if the web app isn't using it.
     - Mirror the web app's actual data layer: import the same fetch helper if one is exported, or call the same third-party services from the mobile app.
     - Skip every instruction below that references `setBaseUrl`, `@workspace/api-client-react`, or `lib/api-spec/openapi.yaml` — those are Mode A only.

   Pick the mode now. The rest of this recipe assumes Mode A unless explicitly marked otherwise.

2. **Read the relevant skills first**

   Before doing anything else, read `.local/skills/expo/SKILL.md` and `.local/skills/mobile-ui/SKILL.md`. These contain the canonical patterns for Expo in this workspace (file-based routing, font loading, `app.json` requirements, mobile UX conventions). Also skim `.local/skills/pnpm-workspace/SKILL.md` for the workspace conventions you'll inherit.

3. **Inspect the existing web artifact (ONE parallel batch)**

   - `ls artifacts/` — confirm the web artifact's slug
   - `cat artifacts/<web-slug>/package.json`
   - `ls artifacts/<web-slug>/src/` (or wherever the source lives)
   - Read the routing entry point — typically `src/App.tsx` / `src/main.tsx` or the routes module — to enumerate screens
   - Read 1-2 representative screens to see how they consume the data layer (Mode A: `@workspace/api-client-react` hooks; Mode B: fetch helper or third-party SDK)
   - Mode A: `cat lib/api-spec/openapi.yaml` (skim — confirms the endpoints you have)

   After reading, write down: (a) the list of screens to port, (b) the auth pattern (if any), (c) the primary data hooks or fetch calls the web app uses.

4. **Create the Expo artifact**

   ```js
   await createArtifact({
     artifactType: "expo",
     slug: "<web-slug>-mobile",
     previewPath: "/",
     title: "<Web Title> Mobile",
     description: "<short paragraph: what the mobile app is, what it does, and who it is for>",
   })
   ```

   Then `pnpm install` at the workspace root. If install fails, fix the error and retry — do not skip.

5. **Configure `app.json`**

   Set `name`, `slug`, and `bundleIdentifier` (e.g. `com.replit.<webslug>mobile`) so Expo Launch can build. Keep the scaffold's `expo-router` plugin, `expo-font` plugin, `typedRoutes: true`, and the Replit `origin` — those are required, do not remove them.

6. **Wire up the data layer**

   *Mode A only — skip in Mode B.*

   In `artifacts/<web-slug>-mobile/app/_layout.tsx`, at module level (before the component):

   ```ts
   import { setBaseUrl } from "@workspace/api-client-react";
   const domain = process.env.EXPO_PUBLIC_DOMAIN;
   if (domain) setBaseUrl(`https://${domain}`);
   ```

   The Expo scaffold ships its own `QueryClient` — either created locally in `app/_layout.tsx` (`new QueryClient()`) or imported from `@/lib/query-client` in newer scaffolds. Use whichever the scaffold ships. `@workspace/api-client-react` does **not** export a `queryClient`; it only exports the generated API surface plus `setBaseUrl` and `setAuthTokenGetter`.

   **Mode B:** If the web app exports a fetch helper (e.g. `lib/api/client.ts`), import it the same way. If the web app calls a third-party API (e.g. Supabase, Firebase) directly, configure the same SDK in the mobile app — do not route through a non-existent backend.

7. **Translate screens** (one screen at a time, simplest first)

   For each web screen identified in step 3, create the matching expo-router file under `app/`:
   - Top-level route → `app/index.tsx`
   - Tabs (if the web app has primary navigation) → `app/(tabs)/<name>.tsx`
   - Detail / modal screens → `app/<name>.tsx`

   For each screen:
   - Reuse the same data layer the web app uses — Mode A: the `@workspace/api-client-react` hooks; Mode B: the web app's exported fetch helper or the third-party SDK.
   - Replace web layout primitives (`div`, `button`, Tailwind classes) with React Native equivalents (`View`, `Pressable`, `StyleSheet.create()`).
   - Replace router calls: `useNavigate()` / `<Link>` → `router.push('/x')` from `expo-router`.
   - Use design tokens from a `constants/colors.ts` file (create one if needed) — do not inline hex values.
   - Prefer mobile-native patterns (bottom tabs, swipe gestures, native pickers) over literal copies of desktop layouts.

8. **Auth (if the web app has login)**

   **Mirror whatever auth stack the web app uses — do not pick a different one.** Migrations from authenticated imports often rewrite the original auth (e.g. Lovable's `supabase.auth.*`, Base44's `base44.auth.*`) into Clerk, while other paths land on Replit Auth. Whatever is in `artifacts/<web-slug>/` is what the mobile app must reuse, so the user's session is shared end-to-end and the same backend authorizes both clients.

   To detect what's in use, in one parallel batch:
   - `cat artifacts/<web-slug>/package.json` — look for `@clerk/clerk-react`, `@clerk/expo`, or a Replit Auth helper.
   - Search the web artifact for sign-in / session calls (e.g. `useUser`, `useAuth`, `SignIn`, `SignedIn`, `useSession`, `signInWithGoogle`).
   - Check `artifacts/api-server/` for the auth middleware (Clerk vs Replit Auth headers).

   Then implement the matching mobile flow:
   - **Clerk** → follow `.local/skills/clerk-auth/SKILL.md` (Expo setup section). Use `@clerk/expo` (not `@clerk/clerk-expo`), wire `<ClerkProvider>` in `app/_layout.tsx` with the `tokenCache` from `@clerk/expo/token-cache`, and reuse the web app's publishable key.
   - **Replit Auth** → follow `.local/skills/replit-auth/SKILL.md`.
   - **(Mode A only) Both auth paths require `setAuthTokenGetter` from `@workspace/api-client-react`** so the generated API client attaches a bearer token to every request. Without it, sign-in succeeds but every protected backend call goes anonymous and 401s. Wire it in a layout that runs after the auth provider mounts (e.g. `(home)/_layout.tsx`); the canonical snippets live in the `clerk-auth` and `replit-auth` skills. Mode B: thread the token through whatever data layer the web app uses.
   - **Other** → ask the user before inventing a new flow.

   Do not roll your own session handling. Mode A: do not duplicate the auth backend — both clients hit the same `artifacts/api-server/`.

9. **Verify the app runs**

   Restart the Expo workflow and check that Metro bundles without errors. If there are runtime errors, read the Metro output, fix, and restart. Do not run `pnpm run build` manually — the workflow handles env vars and build automatically.

10. **Pre-completion checklist**

    - [ ] All web screens have a mobile counterpart under `app/`?
    - [ ] (Mode A) All API calls go through `@workspace/api-client-react` / (Mode B) the mobile app uses the same data-layer approach as the web app?
    - [ ] `app.json` has a valid `name`, `slug`, `bundleIdentifier`?
    - [ ] (Mode A) `setBaseUrl` is wired in `_layout.tsx`?
    - [ ] Workflow restart bundles cleanly and the app renders on the Expo preview?

11. **Propose follow-up tasks**

    Before completing, call `proposeFollowUpTasks` with the three tasks below in a single call. Now that the user has both a web app AND a mobile companion, suggest the natural next steps that turn the project into something they can show off and ship.

    Do not prescribe the exact `createArtifact` API in the task descriptions — the agent who picks up the follow-up will consult the create-artifact skill for the correct `artifactType` and other parameters. Just describe the artifact / outcome.

    1. **"Make a promo video for your app"** (category: `next_steps`) — a **brand-new video artifact (Replit animation)** alongside the web and mobile apps. The description must make clear this is a separate artifact, not a modification of either app and not just a screen recording — it's a short animated showcase built in Replit's video tooling that highlights the app's best features with motion graphics.
    2. **"Create a pitch deck for your app"** (category: `next_steps`) — a **brand-new slides artifact** alongside the web and mobile apps. The description must make clear this is a separate artifact presenting the app's value proposition, core features, and key user flows for demos and stakeholders.
    3. **"Set up push notifications & deep linking"** (category: `next_steps`) — extend the mobile app with Expo push notifications and deep links so users get re-engagement signals and shareable URLs back into specific screens. The description should call out that this builds on the mobile companion, not the web app, and requires additive backend support (token registration endpoint).

12. **Call `markTaskComplete({ task_ref: "<your assigned task ref>", ... })` as the final callback in CodeExecution, then STOP.** Do not send any further messages. Do not propose new features. Do not offer enhancements. Do not ask "what's next?". Do not propose an app icon, polish, or App Store work. The follow-up tasks proposed in step 11 are how the user engages with next steps; the user will inspect the running mobile app on the preview themselves.

## Note to the code reviewer

When reviewing the diff for this task:

- **HONOR `Out of scope`.** Do NOT reject for items explicitly marked out of scope (e.g. typecheck errors, `any` types — explicitly permitted).
- **Do NOT reject for differences from the web app's exact layout.** Mobile-native patterns are the goal; pixel-for-pixel parity is not.
- **Do NOT flag unused scaffold files** (default `components/ui/*`, default `assets/`). Focus on files the agent actually wrote.
- **DO reject changes to `artifacts/<web-slug>/`** — the web artifact must stay untouched. Any diff there is a scope leak.
- **For `artifacts/api-server/` and `lib/*`:** additive changes are allowed (new endpoints, new fields, new columns) when mobile parity needs them. Reject only if the change modifies or removes something the web app already depends on, i.e. anything that breaks the existing web contract.
- **Apply only the criteria from `## Goal` + `## In scope`.** Reject only for real regressions (mobile app fails to bundle, screens missing, breaking changes to existing backend behavior, web artifact touched).

## Expo-specific pitfalls

- **Do not change `app.json` to `app.config.ts`.** Static `app.json` is required — dynamic config breaks Expo Launch.
- **Native package versions** — Expo has strict version requirements. If you `pnpm add` a native module, use `npx expo install` instead so it picks the SDK-compatible version.
- **`expo-router` is filesystem-based** — every file under `app/` is a route. Don't put helper components there; put them under `components/`.
- **Don't port web-only libraries.** `react-router-dom`, `wouter`, `framer-motion` (sometimes), Tailwind classes, raw `<div>` — none of these work in React Native. Find the React Native equivalent.
