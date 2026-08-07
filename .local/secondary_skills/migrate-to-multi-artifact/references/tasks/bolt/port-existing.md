# Port the imported Bolt app

## Goal

The user just imported a project from bolt.new. Port it from the imported state into the Replit `pnpm_workspace` stack so it runs cleanly in this environment. **It must look and work like the original.**

This app is the user's real product. Treat it like porting someone's live app — every lost feature, broken style, or missing interaction is a regression.

## In scope

- Restructure the imported tree into the Replit `pnpm_workspace` layout (frontend artifact + optional `api-server`).
- Make the app actually run via the Replit workflow (HMR + preview pane).
- Wire any external services the imported app uses (database, auth, storage, AI integrations) to Replit equivalents — see `.local/secondary_skills/replit-migration-guardrails/SKILL.md`.

## Out of scope

- Building new features or refactoring beyond what's needed to run.
- Strict typecheck — use `// @ts-ignore` to keep moving. Visual + functional parity matters more than zero TS errors.
- Fixing bugs that existed before the import.

## Bolt-specific notes

Bolt projects vary widely. Detect the shape first instead of assuming.

- **`.bolt/`, `bolt.config.*`, `stackblitz.json`** — StackBlitz-only metadata. Safe to ignore; nothing inside affects runtime on Replit.
- **Most Bolt apps are Vite + React** (sometimes SvelteKit / Astro / Next.js — check `package.json` + config files).
  - Vite + React → follow the steps below; this is the default path.
  - Next.js → STOP. Next.js does not migrate cleanly to `pnpm_workspace`. Inform the user that auto-migration is skipped for Next.js Bolt projects and run the project as-is via expert mode.
  - Other frameworks → Inform the user the framework isn't auto-supported; run as-is.
- **Backend shape** — Bolt apps usually ship as frontend-only (API calls go to third-party services). If there's no `server/` directory and no Express/Fastify/Hono entry, treat as **frontend-only** and skip the backend copy step (step 3 below).
- **Bolt env handling** — Bolt uses Vite-style `import.meta.env.VITE_*`. Keep that convention. Replit secrets surfaced as `VITE_*` env vars are read the same way.

## Pre-existing scaffold (do NOT remove)

The pnpm_workspace scaffold is already applied. These existed before this task started:

- `artifacts/api-server/` — backend artifact (kind=api).
- `artifacts/mockup-sandbox/` — design/mockup artifact.
- `lib/api-spec/`, `lib/api-client-react/`, `lib/db/` — shared packages.

The existing app's frontend goes into a NEW web artifact created via `createArtifact`. Do NOT put frontend code into `artifacts/api-server/`.

## How to communicate

Short, non-technical updates: "Looking at your project..." → "Setting things up..." → "Moving your app..." → "Checking everything works..."

## Steps

### 0. Read the pnpm_workspace skill

Read `.local/skills/pnpm-workspace/SKILL.md` first. It contains the canonical patterns for project references, artifact routing, package management, and common pitfalls.

### 1. Detect + install

```sh
bash .local/secondary_skills/migrate-to-multi-artifact/references/fullstack-detect.sh
pnpm install
```

Read the detect output. Note:

- `CLIENT_DIR` (typically `.` or `src/` for Bolt — flat Vite layout).
- `SCHEMA_PATH` and `ROUTE_LAYOUT` — only relevant if a backend exists.
- `CONFLICTS` — fix these before continuing.

### 2. Read what you need

If a backend exists, read its route file(s) and schema file from `.migration-backup/` (you need their content for the OpenAPI spec).

For frontend-only Bolt apps, read just `package.json` from `.migration-backup/` to capture deps and scripts. Do NOT read the rest — the copy script handles it.

### 3. Copy backend (skip for frontend-only apps)

If the imported app has a real backend:

```sh
bash .local/secondary_skills/migrate-to-multi-artifact/references/fullstack-copy-backend.sh
```

Then write `lib/api-spec/openapi.yaml` based on the routes/schema you read in step 2 (only if practical — small/medium apps). For large legacy backends, skip the spec and keep the existing fetch layer in the frontend.

Run codegen + DB push in parallel:

- `pnpm --filter @workspace/api-spec run codegen`
- `pnpm --filter @workspace/db run push`

Read `lib/api-client-react/src/generated/api.ts` for exact hook names you'll need in step 5.

**Frontend-only Bolt apps**: skip this whole step. The backend copy script will fail (no `server/`) — don't run it.

### 4. Copy frontend

```sh
createArtifact({ artifactType: "react-vite", slug: "<app-name>", previewPath: "/", title: "<Title>", description: "<short paragraph: what the app is, what it does, and who it is for>" })
```

Then run the copy script — do NOT skip this or manually rewrite files instead:

```sh
bash .local/secondary_skills/migrate-to-multi-artifact/references/fullstack-copy-frontend.sh <app-name>
```

The script copies source files from `.migration-backup/` into the new artifact, patches imports, installs dependencies, and handles both flat and nested layouts. Manually rewriting files loses styles, fonts, and subtle markup that the script preserves.

Read the script output and act on it:

- `AGENT TODO` — required edits (vite.config.ts, wouter base path). Do these.
- `SKIPPED` — files intentionally not copied (conflicts). Check if they matter.
- `PATCHED` — automatic fixes applied (fonts, imports). No action needed.
- `INSTALLED` — dependencies added. No action needed.

### 5. Fix frontend imports + preserve app identity

If you wrote an OpenAPI spec, replace old fetch calls with generated hooks from `@workspace/api-client-react`. Otherwise keep the existing fetch layer — just fix paths so they resolve.

Verify these are preserved (the copy script handles most, but check):

- **Fonts** — `index.html` Google Fonts `<link>` tags + CSS `--font-sans` variables.
- **Colors / theme** — if `theme.json` existed, verify it was copied and the vite plugin was wired.
- **Routing** — if using wouter, the `<Router>` must have `base={import.meta.env.BASE_URL}`.
- **Bolt-specific env vars** — anything `import.meta.env.VITE_*` the imported app reads needs a Replit secret with the same name. Use the environment-secrets skill to ask the user for any missing one.

If the original app calls external services directly (Supabase, Firebase, OpenAI / Anthropic / SendGrid / Twilio / Stripe / etc.), follow `.local/secondary_skills/replit-migration-guardrails/SKILL.md` to swap them for Replit equivalents. For auth (Supabase Auth, Firebase Auth, Auth0, etc.), use Clerk — see the authentication skill.

### 6. Verify

Restart the workflow, then use the testing agent (see the testing skill) to exercise the main flows — navigation, key interactions, any auth or data features. The testing agent will screenshot each step and report failures.

**Replit apps run via workflows, not root-level `pnpm dev`.** Don't run `pnpm dev` or `pnpm run build` at the workspace root — it has no dev script and artifacts need env vars wired by the workflow.

**What to check**: Does it look the same? Does it work? If the testing agent reports failures, fix and re-run. If it passes, you're done.

### 7. Propose follow-up tasks

Before completing, call `proposeFollowUpTasks` with the three tasks below in a single call. **The mobile task MUST be the first task in the `tasks` array and MUST be proposed on every Bolt port — this is the single most valuable thing Replit offers that Bolt cannot, and it is the reason many users are porting over.** Do not skip it, do not reorder it. Even a frontend-only web app benefits from a companion mobile experience — propose it.

Do not prescribe the exact `createArtifact` API in the task descriptions — the agent who picks up the follow-up will consult the create-artifact skill for the correct `artifactType` and other parameters. Just describe the artifact to build.

1. **"Take your app mobile"** (category: `next_steps`) — **ALWAYS FIRST. ALWAYS INCLUDED.** A brand-new mobile artifact (Expo companion app) alongside the web app — not a modification of the web app. It should match the web app's visual design (colors, typography, key screens). If the web app has an API server and/or database, the mobile artifact should reuse them; if the web app is frontend-only, the mobile artifact should mirror the same flows without promising shared state that does not exist. Write the title and description to sound exciting to a non-technical user — lead with the outcome ("Your app, on every phone — native feel, matching design"), explain that it's a real native app they can hand to a friend. This is the charm moment for a Bolt user: they shipped a web app, and now Replit gives them a mobile app too.
2. **"Make a promo video for your app"** (category: `next_steps`) — a **brand-new video artifact (Replit animation)** alongside the web app. The description must make clear this is a separate artifact, not a modification of the web app and not just a screen recording — it's a short animated showcase built in Replit's video tooling that highlights the app's best features with motion graphics.
3. **"Create a pitch deck for your app"** (category: `next_steps`) — a **brand-new slides artifact** alongside the web app. The description must make clear this is a separate artifact presenting the app's value proposition, core features, and key user flows for demos and stakeholders.

### 8. Complete

Call `markTaskComplete({ task_ref: "<your assigned task ref>", ... })` as the final callback in CodeExecution. The user will verify visual parity before doing anything else.

## Note to the code reviewer

When reviewing the diff for this task:

- HONOR the `Out of scope` section above. Don't reject for items the plan explicitly marks out of scope (`any` types, typecheck errors).
- Do NOT reject for pre-existing issues — type errors / `any` types / legacy patterns in code copied from the imported tree are not regressions.
- Do NOT flag the pre-existing scaffold packages (`artifacts/api-server/`, `lib/*`) as agent additions.
- Do NOT reject for `pnpm dev` failing at workspace root — Replit apps run via workflows.
- Do NOT flag scaffold files (`src/components/ui/*.tsx` shadcn, default `favicon.svg`).
- Apply only the criteria from this task's `## Goal` + `## In scope`. Reject only for real regressions (broken runtime, missing files, lost features).
