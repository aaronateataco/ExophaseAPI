# Turn the imported Claude design into a real app

## Goal

The user imported a design from Claude. It has **already been set up as a real Replit app**: this repl is a `pnpm_workspace` and the imported design renders right now through a `react-vite` web artifact at `artifacts/claude-design/` — the design's HTML is that artifact's `index.html`, served by Vite at `/`. Your job is to build the **full, working app the design implies** — the frontend *and*, when the design implies data, accounts, or anything dynamic, the backend that powers it — all in this task. **It must keep looking exactly like the imported design**, and the static mockup should become a working product: forms submit and persist, auth works, lists and dashboards show real data, navigation works.

Do not stop at a clickable frontend with mocked data and defer the rest to follow-ups. If the design shows a feature, build it end-to-end in this task. The only things that move to follow-ups are a separate **mobile** app and a promo **video** (see step 4).

The app **boots** as the `react-vite` web artifact, but that is the starting point, not a guaranteed destination — look at the actual design before committing to a plan. Most Claude designs are web apps and the default path below (refactor in place into idiomatic React in the same artifact, plus a backend when needed) is correct. But a design can clearly read as a **mobile app** (phone-frame layout, native navigation patterns), or the user may say they want one. When that's the case, build toward the mobile target instead of forcing the web artifact — and say so in your plan.

The imported markup is the user's real design work — every lost style, font, or layout detail is a regression they'll notice.

## In scope

- Refactor the embedded markup in `artifacts/claude-design/` into idiomatic React components.
- Preserve the design exactly — markup, layout, colors, fonts, and assets.
- Build **every feature and flow the design shows**, fully working: navigation between sections/pages, form inputs that submit, auth/login if a login or account screen is shown, hover/active states, and obvious buttons.
- **Build the backend when the design implies it** — any data, accounts, lists, dashboards, saved state, or login. Fill in the scaffolded `api-server` artifact (and `lib/db` for persistence), expose the endpoints the screens need, and wire the frontend to those real endpoints instead of mocks. Only fall back to local/in-memory state when the design clearly implies no persistence at all.

## Out of scope

- Building features or screens the design doesn't show. (Build everything it *does* show — including its backend — but don't invent new product surface.)
- Re-scaffolding the workspace, recreating the `claude-design` artifact, or moving the repl — it is **already** a `pnpm_workspace` with the `claude-design` artifact registered and running. Do not run a scaffold step and do not call `createArtifact` for `claude-design`. (Building out the pre-scaffolded `api-server` artifact is expected, not a re-scaffold.)
- Strict typecheck — use `// @ts-ignore` to keep moving. Visual + functional parity matters more than zero TS errors.

## Screenshotting in this workspace (read before every screenshot)

This is a multi-artifact `pnpm_workspace`, not a single-artifact Replit app, so the usual screenshot assumptions don't hold. Do this in order — one workflow-ready check plus one cheap probe turns three failed screenshot attempts into a single successful one:

1. **Confirm the workflow is running first.** List the configured workflows and restart the artifact's exact entry — managed artifact workflows are named `<artifact-path>: <Service>` (e.g. `artifacts/claude-design: web`, `artifacts/api-server: API Server`), not the bare artifact name — then wait until the logs show Vite ready / a bound port. Screenshotting a cold server is a guaranteed first failure — never screenshot before the server is up.
2. **`curl`-probe the dev domain before the (expensive) screenshot.** Cheap health check:

```bash
curl -s -o /dev/null -w "%{http_code}" "https://$REPLIT_DEV_DOMAIN/"
```

`200` means the screenshot will succeed. Anything else (`000`, `502`, …) means fix the **server**, not the screenshot call — then re-probe.

3. **Screenshot through the transport the probe proved works.** The screenshot tool's `appPreview` source dials the in-container proxy (`localhost:80`); in a multi-artifact workspace that proxy often refuses connections (`curl` → `000`) even while the app is live on the dev domain. When the probe shows the dev domain answers `200` but `localhost:80` doesn't, screenshot with the tool's **`externalUrl`** source against `https://$REPLIT_DEV_DOMAIN/` — don't keep retrying the `appPreview` proxy transport that just failed.
4. **Never assume port 5000.** That's the single-artifact port. Here each artifact gets its own internal port behind the proxy/dev domain, so resolve the URL from the environment (`$REPLIT_DEV_DOMAIN`), never a guessed port.

## Order of operations (do NOT reorder)

### 0. Understand the rendering design first

The design already renders in the preview — leave it running. Screenshot the live preview to capture how it actually looks — that screenshot is the ground truth for the visual-parity check in step 3. Follow **Screenshotting in this workspace** above (confirm the workflow is up → `curl`-probe `$REPLIT_DEV_DOMAIN` → screenshot via `externalUrl` if the proxy refuses) so this is one shot, not three. Read `artifacts/claude-design/index.html` (the imported design) to understand its structure, content, and intent.

From the screenshot and the markup, decide what the design is actually meant to be — a **web app** (the default; follow steps 1–2 below) or a **mobile app** (phone-frame layout, native nav). Don't assume web just because it boots that way. If the design reads as mobile, your plan should build toward a mobile app (a brand-new Expo artifact that matches the colors, typography, and screens) instead of refactoring the web artifact in place, and you can drop the "Take your app mobile" follow-up since you're already building it.

Then tell the user, in plain non-technical language, what "real" means for this specific design — conversational and outcome-first, not a numbered spec. Name the target when the design points to one, and name the working features you'll build (including the backend behind them when the design needs data or accounts). For example: "Your design looks great and it's already live. Right now it's just the look; I'll make the [signup / cart / dashboard] actually work — accounts that log in, [items] that save and come back when you reload — so it's a real working app, not a mockup." Lead with what they'll be able to do, name the one or two flows that matter most, and skip the jargon. Don't ask for permission to proceed — state the plan and move on.

### 1. Refactor the embedded design into React

The artifact currently serves the imported design as a raw `index.html`. Turn it into an idiomatic `react-vite` app **without changing how it looks**:

- Move the imported markup into the react-vite entry (`src/main.tsx` / `src/App.tsx`) and components, mounting at `#root`. Keep the imported `<head>` assets — Google Fonts `<link>` tags, CSS custom properties / theme variables, inline styles — intact (in `index.html` or imported CSS).
- Split the single page into components/routes as the design implies, but do not redesign — match the imported look exactly.
- Note what's mocked as you read: hardcoded lists, placeholder values, dead buttons, static counts. These are the checklist for step 2 — every one becomes real (backed by the backend when it implies persistence, local state only when it clearly doesn't).
- Keep the artifact's `vite.config.ts` (it wires `PORT` / `BASE_PATH` for workspace routing). If the design uses client-side routing, the router must respect `import.meta.env.BASE_URL`.

**Polish only where the static mockup is silent — never restyle the given look.** The imported design's typography, colors, spacing, and layout are the source of truth; do not "premium-ify" or modernize them. Add what a flat mockup only *implies*:

- **Responsive behavior** — make it work on small screens (stack columns, fluid grids, readable type) while preserving the desktop look exactly.
- **Interaction states** — `hover:` / `active:` / `focus:` states and smooth `transition` on interactive elements, matching the design's existing colors.
- **Loading / empty / pending states** — anything async (a form submit, a fetch) needs a visible pending state.

If a `design` skill is available (`.local/skills/design/SKILL.md`), use it for the polish patterns above — but it never overrides the imported look.

### 2. Build the backend and wire every feature real

This is what makes it a real app, not a clickable mockup — do not skip it or push it to a follow-up. For each feature the design shows, make it actually work end-to-end:

- **Stand up the backend when the design implies data, accounts, or saved state** (lists, dashboards, feeds, carts, profiles, login/signup, anything that should persist). Build it into the **pre-scaffolded `api-server` artifact** — do not re-scaffold or create a new one — and use `lib/db` for persistence. Consult the `pnpm-workspace`, `database`, and `api-spec` skills for how the artifacts, schema, and endpoints fit together.
- **Wire the frontend onto real endpoints.** Replace every mock from step 1 (hardcoded lists, placeholder counts, dead submit buttons) with real calls to the `api-server`. Forms persist, auth logs in and gates the right screens, lists reflect stored data.
- **Only stay frontend-only when the design clearly implies no persistence** (a static marketing/landing page, a calculator with no saved state). In that case "real" just means the interactions work in the browser.
- Keep the look identical throughout — the backend changes what the screens *do*, never how they *look*.

### 3. Verify — including visual parity against the original

Restart the exact artifact workflows (`artifacts/claude-design: web`, and `artifacts/api-server: API Server` if you built it — confirm the names against the workflow list rather than guessing) and wait until each is up, then use the testing agent to walk the app and exercise the interactions; it screenshots each step. **Replit apps run via workflows, not a root-level `pnpm dev`.** Apply **Screenshotting in this workspace** here too — probe `$REPLIT_DEV_DOMAIN` first and screenshot the transport that answers, don't burn attempts on a cold server or the `localhost:80` proxy.

Walk the *real* flows, not just the clickthrough: submit a form and confirm it persists, log in and confirm gated screens appear, reload and confirm data is still there. A feature that only looks wired is not done.

Then do a visual-parity pass — this is the bar the user judges you on. Compare the testing agent's screenshots against the screenshot you took in step 0 of the originally-rendered design:

- Typography (font family, weights, sizes), colors, spacing, and layout must match the imported design.
- Check the responsive view too — the small-screen layout should be a faithful reflow of the same design.

If anything drifted, fix it and re-run. Do not complete until the app looks like the imported design **and** the features actually work end-to-end.

### 4. Propose follow-up tasks

The backend and the design's features are already built in this task — they are **not** follow-ups. Before completing, call `proposeFollowUpTasks` with the tasks below in a single call. **For the web path, the mobile task MUST be first and MUST be proposed** — turning a design into a real app *and* a native mobile app is the charm moment for the user. (Skip the mobile follow-up only if you already built the app as a mobile target — then lead with the video follow-up.)

Do not prescribe the exact `createArtifact` API in the descriptions — the agent who picks up the follow-up consults the create-artifact skill. Just describe the artifact to build.

1. **"Take your app mobile"** (category: `next_steps`) — **ALWAYS FIRST (web path).** A brand-new mobile artifact (Expo) that matches the design's colors, typography, and key screens. Lead with the outcome ("Your design, as a real native app on every phone").
2. **"Make a promo video for your app"** (category: `next_steps`) — a brand-new video artifact (Replit animation) showcasing the design in motion. Not a screen recording.

### 5. Complete

Call `markTaskComplete({ task_ref: "<your assigned task ref>", ... })` as the final callback in CodeExecution. The user will verify visual parity and that the features work before anything else.

## Note to the code reviewer

When reviewing the diff for this task:

- HONOR the `Out of scope` section. Don't reject for items it marks out of scope (e.g. `any` types, typecheck errors, features the design doesn't show).
- Building out the `api-server` artifact and `lib/db`, and adding endpoints/schema, is **in scope** for this task — do not flag the backend as scope creep. (Still don't flag the pre-existing scaffold packages — `artifacts/api-server/`, `artifacts/mockup-sandbox/`, `lib/*` — as agent additions.)
- A feature the design shows that was left mocked/non-functional when it clearly implies persistence (a form that doesn't save, a login that doesn't gate, a list that isn't backed by data) **is** a valid rejection — the task is to ship the full working app, not a clickable mockup.
- Do NOT reject for `pnpm dev` failing at workspace root — Replit apps run via workflows.
- The look must be unchanged from the imported design; flag restyling as a regression, not the absence of it.
- Apply only this task's `## Goal` + `## In scope`. Reject for real regressions (broken runtime, lost styles, missing content, unreachable sections) and for features the design shows that don't actually work.
