# Build the imported Figma design

## Goal

The user imported a design from figma.com. High-fidelity React + Tailwind code was generated from that design and moved to `.migration-backup/` by the scaffold. Turn it into a running web app in the Replit `pnpm_workspace` stack as a single artifact named `figma-design`. **It must look like the design.**

The generated code is a faithful *rendering* of the design, not a finished app — it has the screens, components, theme, and assets, but interactions (navigation, forms, hover/active states) are mostly static. Your job is to get it running as an artifact and wire up the obvious interactions the design implies.

## In scope

- Move the generated design into a new `figma-design` web artifact (`artifacts/figma-design/`) and make it run via the Replit workflow.
- Preserve the design exactly — every screen, component, color, font, and asset.
- Wire the interactions the design implies (routing between screens, form inputs, hover/active states, obvious buttons).

## Out of scope

- Building a backend, database, or auth — a Figma import is frontend-only. If the design implies one, propose it as a follow-up.
- New features or screens beyond what the design shows.
- Strict typecheck — use `// @ts-ignore` to keep moving. Visual parity matters more than zero TS errors.

## What the generated code looks like

The Anima generation follows a consistent shape — assume this unless detection says otherwise:

- **Vite + React** under `.migration-backup/client/` (`client/src/`, `client/index.html`).
- **Tailwind v3 + shadcn**: `client/src/index.css` with `@tailwind base`, `tailwind.config.ts` at the backup root, `client/src/components/ui/*` for the shadcn registry.
- **Screens** under `client/src/pages/*` (one per imported frame), wired into `client/src/App.tsx` as routes.
- **Exported assets** under `client/public/figmaAssets/*` (icons, images extracted from the design).
- **No backend** — there is no `server/` directory and no data/auth layer.

## Pre-existing scaffold (do NOT remove)

The pnpm_workspace scaffold is already applied. These existed before this task started — they are not your additions and you do not need them for a frontend-only design:

- `artifacts/api-server/` — backend artifact (kind=api). Leave it alone.
- `artifacts/mockup-sandbox/` — design/mockup artifact. Leave it alone.
- `lib/api-spec/`, `lib/api-client-react/`, `lib/db/` — shared packages. Leave them alone.

## How to communicate

Short, non-technical updates: "Looking at your Figma design..." → "Setting up your app..." → "Bringing your screens over..." → "Wiring up the navigation..." → "Checking it looks right..."

## Steps

### 1. Register the `figma-design` artifact, then overlay the design

The imported design is a complete, working Vite app in `.migration-backup/`
(react 18, react-day-picker 8, tailwind 3, its own `vite.config.ts`). Two steps,
in order:

**1a. Create the artifact** so it is actually registered — a port is allocated,
`.replit-artifact/artifact.toml` is written, the dev workflow is generated, and
the Run button is wired:

```
createArtifact({ artifactType: "react-vite", slug: "figma-design", previewPath: "/", title: "<the design's title>", description: "<short paragraph: what the app is, what it does, and who it is for>" })
```

This is required even though the next step discards the scaffolded template
files: dropping a folder + hand-written `artifact.toml` on disk is **not** picked
up (pid2's artifact watcher only discovers artifacts created through
`createArtifact`), so the artifact would never get a workflow.

**1b. Overlay the design** — replace the react-vite template files with the
Anima design as-is, keeping the generated `artifact.toml`:

```sh
bash .local/secondary_skills/migrate-to-multi-artifact/references/figma-setup.sh
```

It keeps `.replit-artifact/`, copies `.migration-backup/` in verbatim (no
Tailwind/JSX/react-day-picker conversion — the design ships its own
`package.json` + `vite.config` that already match its code), sets the package
name to `@workspace/figma-design`, points `dev`/`build` at Vite, makes Vite read
the platform `PORT`, fixes Anima's CSS entry (hoists `@import` above the
`@tailwind` directives, drops the stray pre-`base` `@tailwind` block), repairs
Google Fonts imports whose weight lists contain `var()` tokens, converts the
CommonJS tailwind/postcss configs to ESM (`require()` → `import`,
`module.exports` → `export default`), and runs `pnpm install`. Start the
workflow only after it finishes (the Vite binary is installed then).

### 2. Wire the design up + verify

The screens render but are mostly static. Make the design feel real, then
confirm it:

- **Routing** — register every page from the app's `App.tsx` as a route so each
  imported frame is reachable.
- **Interactions** — wire the obvious ones the design implies (nav links,
  buttons, form inputs, hover/active states). Don't invent flows the design
  doesn't show.
- **Verify** — start the workflow, then use the testing agent to walk each
  screen and exercise navigation; it screenshots each step. Replit apps run via
  workflows, not a root-level `pnpm dev`. Fix and re-run until it looks like the
  design and every screen is reachable.

If a typecheck flags issues, they're design-specific (the app's own deps already
match its code — no Tailwind/JSX/react-day-picker version fixes needed). Fix
them before relying on the preview.

### 3. Propose follow-up tasks

Before completing, call `proposeFollowUpTasks` with the tasks below in a single
call. **The mobile task MUST be first and MUST be proposed on every Figma
import** — turning a design into a real app *and* a native mobile app is the
charm moment for a Figma user.

Do not prescribe the exact `createArtifact` API in the descriptions — the agent
who picks up the follow-up consults the create-artifact skill. Just describe the
artifact to build.

1. **"Take your design mobile"** (category: `next_steps`) — **ALWAYS FIRST.** A
   brand-new mobile artifact (Expo) that matches the design's colors,
   typography, and key screens. Lead with the outcome ("Your design, as a real
   native app on every phone").
2. **"Add a backend to your app"** (category: `next_steps`) — only if the design
   implies data or accounts (lists, forms, login screens). A new `api-server`
   artifact + `lib/db` so the static screens become a working product.
3. **"Make a promo video for your app"** (category: `next_steps`) — a brand-new
   video artifact (Replit animation) showcasing the design in motion. Not a
   screen recording.

### 4. Complete

Call `markTaskComplete({ task_ref: "<your assigned task ref>", ... })` as the final callback in CodeExecution. The user will verify visual parity before anything else.

## Note to the code reviewer

When reviewing the diff for this task:

- HONOR the `Out of scope` section. Don't reject for items it marks out of scope (e.g. `any` types, typecheck errors, a missing backend).
- Do NOT reject for pre-existing issues in code copied from `.migration-backup/`.
- Do NOT flag the pre-existing scaffold packages (`artifacts/api-server/`, `artifacts/mockup-sandbox/`, `lib/*`) as agent additions.
- Do NOT reject for `pnpm dev` failing at workspace root — Replit apps run via workflows.
- Do NOT flag scaffold files (shadcn `src/components/ui/*.tsx`, default `favicon.svg`).
- Apply only this task's `## Goal` + `## In scope`. Reject only for real regressions (broken runtime, missing screens, lost styles, unreachable pages).
