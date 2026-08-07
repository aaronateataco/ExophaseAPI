# Port existing app

## Goal

Move the existing app from `.migration-backup/` into the new workspace. It must look and work exactly like before.

**This app is the user's real product.** They built it, their users depend on it, and they trust you not to break it. Every lost feature, broken style, or missing interaction is a regression they'll notice. Treat this like porting someone's live production app — because it is.

## In scope

- Porting the project — copying files, fixing imports, connecting to the API
- Making it look and function identically to the original
- Adapting to the restructured workspace — the scaffold has already added `artifacts/api-server/` (backend), `artifacts/mockup-sandbox/` (pre-existing), `lib/*` packages, and may shift ports. Your job is to fit the existing app into this new layout, not relitigate it.
- **Creating a new web artifact for the existing frontend** via `createArtifact({ artifactType: "react-vite", previewPath: "/", ... })`. The existing website's UI goes into THIS new artifact.

## Out of scope

- Building the new app — that's the next task
- New features, refactoring, or code quality improvements
- Fixing bugs that existed before migration
- Strict typecheck compliance — use `// @ts-ignore` or type assertions to keep moving. Functionality and visual parity matter more than zero TS errors

## Pre-existing scaffold (do NOT remove or relitigate)

The pnpm_workspace scaffold is already applied before this task begins. The following packages existed **before any agent work** — they are not your additions:

- `artifacts/api-server/` — backend artifact (kind=api). The backend goes here.
- `artifacts/mockup-sandbox/` — design/mockup artifact (pre-existing).
- `lib/api-spec/` — OpenAPI spec package.
- `lib/api-client-react/` — generated React hooks package.
- `lib/db/` — database package.

**The existing website's FRONTEND must live in its OWN new web artifact**, e.g. `artifacts/<app-name>/` created via `createArtifact({ artifactType: "react-vite", previewPath: "/", ... })`. **Do NOT put frontend code into `artifacts/api-server/`** — that artifact is kind=api and will not appear in the website preview pane.

## Note to the code reviewer

When reviewing the diff for this task:

- **HONOR the `Out of scope` section above.** Do NOT reject for items the plan explicitly marks out of scope (e.g. `any` types, typecheck errors — those are explicitly permitted).
- **Do NOT reject for pre-existing issues.** Type errors, `any` types, and legacy patterns in code copied from `.migration-backup/` are not regressions. The goal of a port is behavior parity, not refactor.
- **Do NOT flag the pre-existing scaffold packages** listed above as agent additions. They existed before the task started.
- **Do NOT reject for `pnpm dev` / `pnpm run dev` failing at workspace root.** Replit apps run via workflows (`restart_workflow`), not root-level `pnpm dev`. If the agent verified the app via workflow and it works, that is correct.
- **Do NOT flag unused scaffold files** (e.g., `src/components/ui/*.tsx` shadcn components, default `favicon.svg`). These come with `createArtifact` and are meant to be available. Focus on files the agent actually wrote or changed.
- **Apply only the criteria from this task's `## Goal` + `## In scope`.** Reject only for real regressions (broken runtime, missing files, lost features, wrong artifact kind).

## How to communicate

Short, non-technical updates at each phase:

- "Looking at your project..." → "Setting up the database..." → "Moving your app files..." → "Checking everything works..."

## Steps

### 0. Read the pnpm_workspace skill first

Before doing anything else, read `.local/skills/pnpm-workspace/SKILL.md`. It contains the canonical patterns for this workspace (TypeScript project references, artifact routing, package management, logging, common pitfalls). You will need it for every later step.

### 1. Detect + install

```sh
bash .local/secondary_skills/migrate-to-multi-artifact/references/fullstack-detect.sh
pnpm install
```

Read the detect output for `SCHEMA_PATH`, `ROUTE_LAYOUT`, and `CONFLICTS`. Fix any conflicts now.

### 2. Read routes + schema

Read ONLY these from `.migration-backup/` — you need their content for the OpenAPI spec:

- Route file(s) at the path from detect output
- Schema file at `SCHEMA_PATH` from detect output

Do NOT read anything else. The copy scripts handle the rest.

### 3. Copy backend

```sh
bash .local/secondary_skills/migrate-to-multi-artifact/references/fullstack-copy-backend.sh
```

Then do the judgment calls:

- **Convert route signature** — legacy routes export `registerRoutes(httpServer, app)`. For simple routes, convert to an Express router:

  ```typescript
  // artifacts/api-server/src/routes/index.ts — add alongside healthRouter:
  import { Router, type IRouter } from "express";
  import healthRouter from "./health";
  import appRouter from "./routes";
  const router: IRouter = Router();
  router.use(healthRouter);
  router.use(appRouter);
  export default router;
  ```

  For complex setups (middleware, auth, SSE streaming, HTTP server creation), keep `registerRoutes(app)` and wire it into `app.ts` directly. Don't force a Router refactor — functional parity matters more than pattern compliance.

- **Write OpenAPI spec** (if practical): `lib/api-spec/openapi.yaml` based on routes + schema. For small/medium apps (< 20 endpoints), write the full spec and use generated hooks. **For large legacy apps** (many endpoints, custom fetch layer), skip the OpenAPI spec and keep the existing frontend API layer — rewriting every page to use generated hooks is too risky for a port.

- **Run codegen + DB push** (parallel): `pnpm --filter @workspace/api-spec run codegen` and `pnpm --filter @workspace/db run push`
- **Read generated hooks** (if codegen was run): `lib/api-client-react/src/generated/api.ts` — you need exact hook names for step 5

### 4. Copy frontend

```sh
createArtifact({ artifactType: "react-vite", slug: "<app-name>", previewPath: "/", title: "<Title>", description: "<short paragraph: what the app is, what it does, and who it is for>" })
```

```sh
bash .local/secondary_skills/migrate-to-multi-artifact/references/fullstack-copy-frontend.sh <app-name>
```

Read the script output — it tells you what to do next:

- `AGENT TODO` → required edits (vite.config.ts, wouter base path)
- `SKIPPED` → files that were intentionally not copied (conflicts)
- `PATCHED` → automatic fixes applied (fonts, imports)
- `INSTALLED` → dependencies added

### 5. Fix frontend imports + preserve app identity

If you wrote an OpenAPI spec and ran codegen, replace old imports with generated hooks from `@workspace/api-client-react`. Use the exact hook names from step 3. If the frontend already has a working fetch layer and you skipped the OpenAPI spec, keep the existing imports — just fix the paths so they resolve.

Don't rewrite files — targeted edits only. Don't import from `@workspace/db` in frontend code (importing from the DB package triggers database connection code — use generated hooks or keep the existing fetch layer instead).

Also verify these are preserved (the copy script handles most, but check):

- **Fonts** — the original app's fonts must survive. Check `index.html` for Google Fonts `<link>` tags and `index.css` for `--app-font-sans` / `--font-sans`. If the scaffold's default font (Inter) replaced the original, fix it.
- **Colors/theme** — if the old app had a `theme.json`, verify it was copied and the vite plugin was wired up. If it used CSS variables directly, verify `:root` and `.dark` blocks survived the copy.
- **queryClient** — if the old app had a custom `queryClient.ts` with fetch logic or error handling, verify `App.tsx` imports it instead of creating a bare `new QueryClient()`.
- **Routing** — if using wouter, the `<Router>` must have `base={import.meta.env.BASE_URL}` or navigation breaks silently.

### 6. Verify

Restart the workflow and take a screenshot. **Replit apps run via workflows, not root-level `pnpm dev`.**

**What to check:** Does it look the same? Does it work? If yes, you're done. If there are visual differences, fix and restart.

**What NOT to do:**

- Don't run `pnpm dev` or `pnpm run dev` at the workspace root — the root has no dev script by design, and artifacts need env vars (`PORT`, `BASE_PATH`) wired by the workflow. It will fail and you'll waste time debugging a non-issue.
- Don't run `pnpm run build` manually either.
- Don't chase typecheck errors. Don't refactor. Don't "improve" anything. If it looks right and functions right via `restart_workflow`, ship it.

### 7. Complete

Call `markTaskComplete({ task_ref: "<your assigned task ref>", ... })` as the final callback in CodeExecution — the user will verify visual parity before the next task starts.
