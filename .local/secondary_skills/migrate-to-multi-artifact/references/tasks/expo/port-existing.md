# Port existing app

## Goal

Move the existing Expo app from `.migration-backup/` into the new workspace. It must look and work exactly like before.

**This app is the user's real product.** They built it, their users depend on it, and they trust you not to break it. Every lost feature, broken style, or missing interaction is a regression they'll notice. Treat this like porting someone's live production app — because it is.

## In scope

- Porting the project — copying files, fixing imports, connecting to the API
- Making it look and function identically to the original
- Adapting to the restructured workspace — the scaffold has already added `artifacts/mockup-sandbox/`, `lib/*` packages, and scaffold-required `app.json` additions (expo-router plugin, expo-font plugin, typedRoutes, Replit origin). Your job is to fit the existing app into this new layout, not relitigate it.

## Out of scope

- Building the new app — that's the next task
- New features, refactoring, or code quality improvements
- Fixing bugs that existed before migration
- Strict typecheck compliance — use `// @ts-ignore` or type assertions to keep moving. Functionality and visual parity matter more than zero TS errors

## Pre-existing scaffold (do NOT remove or relitigate)

The pnpm_workspace scaffold is already applied before this task begins. The following packages existed **before any agent work** — they are not your additions:

- `artifacts/mockup-sandbox/` — design/mockup artifact (pre-existing).
- `lib/*` — shared packages bundled with the scaffold.

Scaffold-required additions to `app.json` (e.g. `expo-router` plugin, `expo-font` plugin, `typedRoutes: true`, Replit `origin`) are part of the new scaffold and must remain — do not treat them as drift from the original.

## Note to the code reviewer

When reviewing the diff for this task:

- **HONOR the `Out of scope` section above.** Do NOT reject for items the plan explicitly marks out of scope (e.g. `any` types, typecheck errors — those are explicitly permitted).
- **Do NOT reject for pre-existing issues.** Type errors, `any` types, and legacy patterns in code copied from `.migration-backup/` are not regressions. The goal of a port is behavior parity, not refactor.
- **Do NOT flag the pre-existing scaffold packages** above as agent additions, and do NOT reject scaffold-required `app.json` additions as drift.
- **Do NOT reject for `pnpm dev` / `pnpm run dev` failing at workspace root.** Replit apps run via workflows (`restart_workflow`), not root-level `pnpm dev`. If the agent verified via workflow and it works, that is correct.
- **Do NOT flag unused scaffold files** (e.g., default `components/ui/*`, `assets/` files that came with the Expo scaffold). Focus on files the agent actually wrote or changed.
- **Apply only the criteria from this task's `## Goal` + `## In scope`.** Reject only for real regressions (broken runtime, missing files, lost features).

## User communication

Tell the user what's happening at each major phase. Keep it short and non-technical:

- Before starting: "Looking at your project to understand how it's set up..."
- Before backend work: "Setting up the database and API..."
- Before frontend work: "Moving your app files over to the new structure..."
- Before sanity check: "Running a quick check to make sure everything is in the right place..."
- Before build: "Building everything to make sure it works..."
- Before `markTaskComplete`: "Running some checks to make sure your app is safe and sound after the migration. This may take a minute."
- If validation fails: "Found a small issue — fixing it now..."

## Steps

0. **Read the pnpm_workspace skill first**

   Before doing anything else, read `.local/skills/pnpm-workspace/SKILL.md`. It contains the canonical patterns for this workspace (TypeScript project references, artifact routing, package management, logging, common pitfalls). You will need it for every later step.

1. **Detect old project structure and batch-read (ONE parallel call)**

   Include these in your single parallel batch of reads:

   - `ls .migration-backup/` (top-level structure)
   - `ls .migration-backup/client/ 2>/dev/null` (Expo v3 code prefix — exists if non-routing code lives under `client/`)
   - `ls .migration-backup/server/ 2>/dev/null` (determines single-file vs directory routes layout; absent for frontend-only projects)
   - `cat .migration-backup/app/_layout.tsx 2>/dev/null || echo "NO_EXPO_ROUTER"` — determines routing paradigm
   - `cat .migration-backup/package.json` and `cat .migration-backup/app.json`
   - `.migration-backup/server/routes.ts` or files in `.migration-backup/server/routes/` — use the `ls` result above to pick the right one
   - `.migration-backup/shared/schema.ts` or equivalent
   - `cat .migration-backup/<prefix>/constants/colors.ts 2>/dev/null || cat .migration-backup/constants/colors.ts 2>/dev/null` — design token colors
   - `cat .migration-backup/<prefix>/constants/typography.ts 2>/dev/null || cat .migration-backup/constants/typography.ts 2>/dev/null` — font families, sizes, weights (may not exist)
   - `cat .migration-backup/<prefix>/constants/theme.ts 2>/dev/null || cat .migration-backup/constants/theme.ts 2>/dev/null` — unified theme file if it exists

   **After reading, determine two things:**

   a. **Routing paradigm:**
      - **expo-router**: `app/_layout.tsx` exists → screens are files under `app/`, routing is filesystem-based
      - **react-navigation**: no `app/_layout.tsx` → a Navigator tree wires up screens explicitly

   b. **Code prefix** (where non-routing code lives — components, constants, hooks, assets):
      - If `ls .migration-backup/client/` returned a listing → prefix is `client/` (Expo v3 template)
      - Otherwise → prefix is `.` (root-level, older projects)

   Both determinations are required. Do not proceed to step 2 without knowing both.

2. **Run `pnpm install`** — before any other pnpm commands. If it fails, read the error, fix the issue (e.g. remove conflicting packages), and retry.

3. **Port backend** (can run in parallel with step 4; skip entirely if no `server/` or `shared/` directory)

   **Always port ALL server files, even if they contain only stubs or appear unused.** Copy first, fix imports after.

   a. **DB schema** — Always copy the schema even if the app appears to use only local storage. Copy then immediately fix imports:

      ```sh
      cp .migration-backup/shared/schema.ts lib/db/src/schema/
      sed -i 's/from "zod"/from "zod\/v4"/g' lib/db/src/schema/schema.ts
      sed -i 's/from '\''zod'\''/from '\''zod\/v4'\''/g' lib/db/src/schema/schema.ts
      ```

   b. **OpenAPI spec** — Write `lib/api-spec/openapi.yaml` based on the routes you already read.

   c. **Run codegen + DB push** (parallel):
      - `pnpm --filter @workspace/api-spec run codegen`
      - `pnpm --filter @workspace/db run push`

   d. **Read generated hooks** — After codegen completes, read `lib/api-client-react/src/generated/api.ts` to get exact hook names and signatures before fixing frontend imports.

   e. **API routes** — Copy then fix imports. Stock Expo backends ship either a single `server/routes.ts` or a `server/routes/` directory — check which exists:

      ```sh
      # Single-file template (most common):
      cp .migration-backup/server/routes.ts artifacts/api-server/src/routes/routes.ts
      # Directory template:
      cp -r .migration-backup/server/routes/* artifacts/api-server/src/routes/
      # Copy storage layer — always, even if it looks like a stub:
      cp .migration-backup/server/storage.ts artifacts/api-server/src/storage.ts 2>/dev/null; true
      # Copy any other server files (middleware, utils, etc.):
      cp .migration-backup/server/*.ts artifacts/api-server/src/ 2>/dev/null; true
      ```

      **Signature change required:** the legacy export is `registerRoutes(httpServer, app)`. Convert it to an Express router and mount it from `src/routes/index.ts`. Targeted edits: `@shared/` or `../../shared/` → `@workspace/db`, add `@workspace/api-zod` for validation.

4. **Port frontend**

   Always start by creating the artifact — the scaffold must exist before you copy into it:

   ```js
   await createArtifact({ artifactType: "expo", slug: "<app-name>", previewPath: "/", title: "<Title>", description: "<short paragraph: what the app is, what it does, and who it is for>" })
   ```

   Then copy based on the routing paradigm detected in step 1.

   **If expo-router** (old project has `app/_layout.tsx`):

   Copy the directory structure directly — it maps to the new artifact. First, list what's actually in the prefix so you copy everything:

   ```sh
   ls .migration-backup/<prefix>/
   ```

   Then copy every directory that exists (skip `node_modules`, `app/` — that's routing, handled separately):

   ```sh
   cp .migration-backup/app.json artifacts/<app-name>/app.json
   cp -r .migration-backup/app/* artifacts/<app-name>/app/
   # <prefix> is "client" or "." — determined in step 1. Do not guess.
   # Copy directory CONTENTS, not the directory itself — trailing /* prevents nesting:
   cp -r .migration-backup/<prefix>/components/* artifacts/<app-name>/components/
   cp -r .migration-backup/<prefix>/constants/* artifacts/<app-name>/constants/
   cp -r .migration-backup/<prefix>/hooks/* artifacts/<app-name>/hooks/
   cp -r .migration-backup/<prefix>/lib/* artifacts/<app-name>/lib/
   cp -r .migration-backup/<prefix>/assets/* artifacts/<app-name>/assets/
   cp -r .migration-backup/<prefix>/navigation/* artifacts/<app-name>/navigation/
   # Also copy any other directories shown by ls above (e.g. services/, utils/, store/)
   # If a target dir doesn't exist yet, create it first: mkdir -p artifacts/<app-name>/<dir>
   ```

   Do not add `2>/dev/null` — if a `cp` fails, you need to see it. After copying, verify:

   ```sh
   bash .local/secondary_skills/migrate-to-multi-artifact/references/expo-verify-copy.sh <app-name> <prefix>
   ```

   Fix any missing directories before proceeding.

   Always copy `app.json` to preserve `name`, `slug`, `bundleIdentifier`, icons, plugins, and schemes. The `@/` alias in the artifact resolves to `artifacts/<app-name>/`. Since you preserved the same directory structure, all existing `@/components/...`, `@/constants/...`, and `@/assets/...` paths continue to work without changes.

   **If react-navigation** (no `app/_layout.tsx`):

   The old project has a Navigator tree instead of file-based routing. You cannot copy the routing structure — you must translate it:

   a. Copy non-routing code in bulk. First, list what's in the prefix:

      ```sh
      ls .migration-backup/<prefix>/
      ```

      Then copy every directory that exists (skip `node_modules`). Do NOT use `2>/dev/null`:

      ```sh
      # <prefix> is "client" or "." — determined in step 1. Do not guess.
      cp -r .migration-backup/<prefix>/components/* artifacts/<app-name>/components/
      cp -r .migration-backup/<prefix>/constants/* artifacts/<app-name>/constants/
      cp -r .migration-backup/<prefix>/hooks/* artifacts/<app-name>/hooks/
      cp -r .migration-backup/<prefix>/lib/* artifacts/<app-name>/lib/
      cp -r .migration-backup/<prefix>/assets/* artifacts/<app-name>/assets/
      cp -r .migration-backup/<prefix>/navigation/* artifacts/<app-name>/navigation/
      cp -r .migration-backup/<prefix>/screens/* artifacts/<app-name>/screens/
      # Also copy any other directories shown by ls above
      ```

      After copying, verify:

      ```sh
      bash .local/secondary_skills/migrate-to-multi-artifact/references/expo-verify-copy.sh <app-name> <prefix>
      ```

   b. For each screen in the old Navigator tree, create the corresponding expo-router file:
      - Root screen → `app/index.tsx`
      - Tab screen "Home" → `app/(tabs)/index.tsx`
      - Tab screen "Profile" → `app/(tabs)/profile.tsx`
      - Modal screen "Detail" → `app/detail.tsx`

      Copy the screen component's body verbatim. Replace `navigation.navigate('X')` with `router.push('/x')` from `expo-router`.

   c. Verify `@/` alias paths after copying:

      ```sh
      bash .local/secondary_skills/migrate-to-multi-artifact/references/expo-verify-imports.sh <app-name>
      ```

      Fix every broken import before proceeding.

   Copy `app.json` from the old project to `artifacts/<app-name>/app.json`. Verify `name`, `slug`, and `bundleIdentifier` are preserved.

   **Fix frontend imports** (both paradigms — wait for codegen in step 3d to complete first):
   - Replace old fetch hooks with generated hooks from `@workspace/api-client-react`
   - Add `setBaseUrl` in `app/_layout.tsx` at module level (before the component):

     ```typescript
     import { setBaseUrl } from "@workspace/api-client-react";
     const domain = process.env.EXPO_PUBLIC_DOMAIN;
     if (domain) setBaseUrl(`https://${domain}`);
     ```

   - Remove `@shared/` or `../../shared/` imports — types now come from generated hooks
   - Preserve the original `queryClient` configuration — do not create a new one
   - Do not import from `@workspace/db` or server code

5. **Run sanity check** — do NOT move to step 6 until the output prints ALL CHECKS PASSED:

   ```sh
   bash .local/secondary_skills/migrate-to-multi-artifact/references/expo-sanity-check.sh <app-name> <prefix>
   ```

   If any FAIL line appears, fix and re-run until ALL CHECKS PASSED.

6. **Verify the app works** — restart the workflow and check that Metro bundles without errors. Do NOT run `pnpm run build` manually — the workflow handles env vars and build automatically. If there are visual differences, verify that `constants/colors.ts` and `app.json` were copied correctly.

7. **Pre-completion checklist** — verify before marking complete:
   - [ ] ALL backend files ported (routes, storage, schema — even stubs)?
   - [ ] `zod` → `zod/v4` imports fixed in schema files?
   - [ ] `@shared/` → `@workspace/db` imports fixed in all server files?
   - [ ] `app.json` copied with correct name, slug, bundleIdentifier?
   - [ ] App renders correctly after workflow restart?
   - [ ] Sanity check prints ALL CHECKS PASSED?

8. **Call `markTaskComplete({ task_ref: "<your assigned task ref>", ... })` as the final callback in CodeExecution** — the user will verify visual parity before the next task starts.

## Expo-specific pitfalls

- **Do not change `app.json` to `app.config.ts`**: The project must use static `app.json`. Dynamic config files break the Expo Launch build process.
- **Do not modify StyleSheet styles**: Copy component files verbatim. Styling uses `StyleSheet.create()` and `constants/colors.ts`, not CSS/Tailwind.
- **Preserve the font-loading pattern**: The scaffold uses `useFonts` + `SplashScreen` gating in `_layout.tsx`. Copy the old layout's font loading exactly.
- **`expo-router` file-based routing**: The `app/` directory structure IS the routing. Preserve the exact directory hierarchy when copying (expo-router projects only).
- **Do not port infrastructure**: Do not copy DB connection setup (e.g., Neon serverless). The workspace has its own in `lib/db`.
- **Native package versions**: Expo has strict version requirements for native modules (e.g. `react-native-keyboard-controller` 1.21.4 is incompatible with Expo SDK expecting 1.18.5). The sanity check compares versions between the original and the artifact. Always preserve the original project's native package versions — do not upgrade them.
