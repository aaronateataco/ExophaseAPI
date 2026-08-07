# Port existing mockup

## Goal

Move the existing mockup app from `.migration-backup/` into the workspace's mockup artifact (`artifacts/mockup-sandbox/`). It must look and behave exactly like before.

**This mockup is the user's real design work.** Every lost screen, broken style, or missing interaction is a regression they'll notice.

## In scope

- Porting the mockup — copying files, fixing imports and the Vite base path
- Making it look and function identically to the original
- Adapting to the restructured workspace — the scaffold has already added `artifacts/api-server/` (backend), `artifacts/mockup-sandbox/` (where this mockup goes), `lib/*` packages, and may shift ports. Your job is to fit the existing mockup into this layout, not relitigate it.

## Out of scope

- Building a real (production) app from the mockup — that's a follow-up task if the user wants it
- Backend work, OpenAPI specs, or database setup — a mockup has none
- New features, refactoring, or code quality improvements
- Strict typecheck compliance — use `// @ts-ignore` or type assertions to keep moving. Visual parity matters more than zero TS errors

## Pre-existing scaffold (do NOT remove or relitigate)

The pnpm_workspace scaffold is already applied before this task begins. The following packages existed **before any agent work** — they are not your additions:

- `artifacts/api-server/` — backend artifact (kind=api). Leave it alone for this task.
- `artifacts/mockup-sandbox/` — design/mockup artifact. The existing mockup goes HERE.
- `lib/api-spec/`, `lib/api-client-react/`, `lib/db/` — shared packages. Leave them alone for this task.

## Note to the code reviewer

When reviewing the diff for this task:

- **HONOR the `Out of scope` section above.** Do NOT reject for items the plan explicitly marks out of scope (e.g. `any` types, typecheck errors — those are explicitly permitted).
- **Do NOT reject for pre-existing issues.** Type errors, `any` types, and legacy patterns in code copied from `.migration-backup/` are not regressions. The goal of a port is behavior parity, not refactor.
- **Do NOT flag the pre-existing scaffold packages** listed above as agent additions. They existed before the task started.
- **Do NOT reject for `pnpm dev` / `pnpm run dev` failing at workspace root.** Replit apps run via workflows (`restart_workflow`), not root-level `pnpm dev`.
- **Apply only the criteria from this task's `## Goal` + `## In scope`.** Reject only for real regressions (broken runtime, missing files, lost screens, broken styles).

## How to communicate

Short, non-technical updates at each phase:

- "Looking at your mockup..." → "Moving your screens..." → "Checking everything looks right..."

## Steps

### 0. Read the pnpm_workspace skill first

Before doing anything else, read `.local/skills/pnpm-workspace/SKILL.md`. It contains the canonical patterns for this workspace (artifact routing, package management, common pitfalls).

### 1. Install

```sh
pnpm install
```

### 2. Survey the old mockup

List `.migration-backup/` and read its `package.json`, `index.html`, and entry file. You need: the dependency list, fonts/theme setup, and the routing approach. Don't read every component — the copy in step 3 brings them over unchanged.

### 3. Copy the mockup into `artifacts/mockup-sandbox/`

- Copy `src/`, `public/`, `index.html`, and any styles/config the app needs from `.migration-backup/` into `artifacts/mockup-sandbox/`, replacing the scaffold's placeholder content.
- Merge the old `package.json` dependencies into `artifacts/mockup-sandbox/package.json` (dependencies only — keep the artifact's existing scripts and build config), then `pnpm install`.
- Keep the artifact's own `vite.config.ts` (it wires `PORT`/`BASE_PATH` for workspace routing). Port over only app-specific plugin/alias config from the old vite config.

### 4. Preserve app identity

- **Fonts** — check `index.html` for Google Fonts `<link>` tags and the CSS for `--font-sans` variables. If the scaffold's default font replaced the original, fix it.
- **Colors/theme** — verify `:root` and `.dark` CSS variable blocks survived the copy.
- **Routing** — if using wouter or react-router, the router must respect `import.meta.env.BASE_URL` or navigation breaks silently under the artifact path.

### 5. Verify

Restart the workflow and take a screenshot. **Replit apps run via workflows, not root-level `pnpm dev`.**

Does it look the same? Do the screens and interactions work? If yes, you're done. If there are visual differences, fix and restart. Don't chase typecheck errors, don't refactor, don't "improve" anything.

### 6. Complete

Call `markTaskComplete({ task_ref: "<your assigned task ref>", ... })` as the final callback in CodeExecution — the user will verify visual parity before the next task starts.
