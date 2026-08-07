---
name: migrate-to-multi-artifact
description: "Migrate the project to support multiple artifacts -- required before adding a mobile app, web app, slide deck, or any second app alongside the existing one."
---

# Migrate to multi-artifact

## When to use

**If the user asks to add a mobile app (React Native/Expo), a second app, a new artifact, or anything that requires multi-artifact support and their project does not currently support multiple artifacts**, request migration immediately -- do NOT explore the project structure first, and do NOT start building the new app yet. This applies even if you are currently in Mockup Mode or any other restricted mode -- migration always takes priority.

## How to propose a migration

**Step 1: Create plan files.** Before calling `proposeMigration`, each task needs a plan file under `.local/tasks/`. How to create them depends on the task type:

### Migration (port) plan -- COPY the canonical rubric, don't rewrite it

The port plan is essentially the same across every project -- the rubric already has the full Done / In scope / Out of scope / Steps / Note to reviewer content. **Copy it** instead of paraphrasing:

- For **fullstack_js -- pnpm_workspace**:

  ```bash
  cp .local/secondary_skills/migrate-to-multi-artifact/references/tasks/fullstack-js/port-existing.md .local/tasks/port-<slug>.md
  ```

- For **expo -- pnpm_workspace**:

  ```bash
  cp .local/secondary_skills/migrate-to-multi-artifact/references/tasks/expo/port-existing.md .local/tasks/port-<slug>.md
  ```

- For **mockup_js -- pnpm_workspace**:

  ```bash
  cp .local/secondary_skills/migrate-to-multi-artifact/references/tasks/mockup-js/port-existing.md .local/tasks/port-<slug>.md
  ```

Then make any edits that help this specific user. Suggestions (not required):

- **Title**: customize `# Port existing app` to reference the user's actual project. Match the user's language -- if they wrote in Japanese, Chinese, Spanish, etc., the title should be in that language too (e.g. `# --` / `# Port the bakery website` / `# Migrate the finance dashboard`).
- **What & Why**: if you want to add a short paragraph acknowledging the user's specific app, feel free.
- **Any other customization** you think genuinely helps this case.

Avoid: rewriting the Done / Steps / Out of scope / Note to reviewer sections just to paraphrase. Those are the canonical rubric -- edit them only if you're adding information that isn't already there, not to reword what already works.

### Follow-up task plans -- write a full plan per user intent

Follow-ups differ per case (mobile, slides, auth, etc.). Write a real plan file with concrete, inlined steps -- not a stub pointing elsewhere. The agent that picks up this task (it runs in the main session, after the migration merges) reads the plan directly; anything you leave out is content it won't see.

Content conventions:

- **What & Why**: 1-2 sentences tying back to what the user actually asked for. Name the existing app, the new artifact type, and what the new app should do.
- **Done looks like**: outcome-based. Describe what the USER sees/does when the app is working. Backend reuse and component reuse are **preferences** (don't phrase as hard requirements -- it causes reviewer thrashing when endpoints don't exist or when mobile form factors demand rebuilt UI). **Brand/visual reuse IS a hard requirement**, though: same logos, same images, same colors, same fonts -- the new app must look like the same product, not a redesign.
- **Out of scope**: list the real exclusions (e.g., "Rebuilding the backend", "Adding new features beyond what the user asked for").
- **Steps**: inline the full recipe below (adapt the wording to fit the user's ask). Don't write `(see guidance elsewhere)` -- put the steps IN the plan. The last two steps should be `presentArtifact({ artifactId })` -- `markTaskComplete({ task_ref: "<your assigned task ref>", ... })` in CodeExecution, in that order.
- **Relevant files**: the existing app's entry points + any shared libs the new artifact will wire to.
- **Note to the code reviewer** (paste verbatim -- prevents rejection loops).

Template example -- inline it into every follow-up plan, adapting titles/names:

```markdown
# Build <app-name> mobile companion app

## What & Why
The user asked for a mobile companion to their existing <app-type> (<app-name>). The mobile app should give them the same core functionality on phones, with a UI adapted to the mobile form factor.

## Done looks like
- The Expo app runs, loads, and the main user flow works end-to-end.
- It shows the same core data the existing app shows (menu, listings, content -- whatever is central to the user's product).
- **Uses the same brand assets as the existing app** -- the same logos, icons, images, and photos. No placeholder images, no AI-generated defaults, no scaffolded stock content.
- **Uses the same color palette and typography as the existing app** -- pull exact colors from the existing app's theme/CSS variables and use the same font family. Don't invent new ones.
- The mobile UI clearly feels like the same product as the existing app. Platform-native patterns (navigation, tab bars, touch targets) are fine, but the visual identity should match at a glance.

## Out of scope
- Rebuilding the backend.
- Adding features beyond what the user asked for.
- Forcing component reuse when web components don't fit mobile (you can rebuild UI, but keep brand/colors/fonts/images identical to the existing app).

## Steps
1. Read the `artifacts` skill for how to create new apps.
2. Create the new artifact: `createArtifact({ artifactType: "expo", slug: "<app-name>-mobile", previewPath: "/", title: "<Title>", description: "<short paragraph: what the app is, what it does, and who it is for>" })`.
3. **Inventory the existing app's visual identity first.** Before writing mobile UI, read the existing app's theme/CSS files to capture: exact color values (hex/HSL), font families, spacing patterns. List image/logo/icon assets in the existing app's `public/` or `assets/` directory that you'll need.
4. **Copy brand assets into the mobile artifact.** Because Metro (Expo bundler) can't resolve files outside its artifact root, copy (don't symlink) logos, icons, hero images, and content photos from the existing app's assets directory into `artifacts/<app-name>-mobile/assets/`. Use the SAME files, not regenerated alternatives.
5. **Apply the design tokens.** Pull exact colors from the existing app's theme (e.g. from `src/index.css` `:root` CSS variables) and paste them into the mobile artifact's `constants/colors.ts`. Use the same font family names.
6. Build the mobile UI. Component structure can be mobile-native (tabs, native nav), but every color, font, and image should match the existing app. No placeholders -- if the existing app has an image for a menu item, the mobile app uses that same image.
7. Wire up to the backend. Prefer generated hooks from `@workspace/api-client-react` when the endpoints cover what you need. If the backend doesn't yet expose a needed endpoint, it's fine to add one (or use direct fetch) -- whichever is simplest.
8. **Sanity-check BOTH artifacts run + present.** Start the relevant workflows, take a screenshot of the new app AND the existing app side by side, confirm the happy path works end-to-end (not just that the build compiles), AND visually confirm that the brand matches (same logo, same colors, same images -- not placeholders). Then call `presentArtifact({ artifactId })` with the new artifact's stable ID to show it to the user.
9. **Call `markTaskComplete({ task_ref: "<your assigned task ref>", ... })` as the final callback in CodeExecution.**

Order: verify/screenshot -- `presentArtifact({ artifactId })` -- `markTaskComplete({ task_ref: "<your assigned task ref>", ... })` in CodeExecution. Once you call `markTaskComplete`, the session ends, so any earlier step that didn't happen won't happen anymore.

Do not include a deploy-suggestion step in these task plans. Publishing suggestions are handled by the main agent calling `SuggestUserAction({ action: "deploy", message: "The app is ready to publish." })` after task completion.

## Relevant files
- `.replit`, `package.json`, `pnpm-workspace.yaml`
- Existing app's main UI entry points (e.g. `artifacts/<web-app>/src/App.tsx`, page files)
- `lib/api-client-react/src/generated/api.ts` (generated hooks)
- `constants/colors.ts` / equivalent theming files from the existing app

## Note to the code reviewer
Do NOT reject this follow-up task for:
- Not using `@workspace/api-client-react` hooks when the needed endpoints don't exist in the backend (adding the endpoint or using direct fetch is acceptable).
- "Not enough" component reuse -- component structure can be mobile-native; adapted or rebuilt UI is fine across form factors.
- Platform-native navigation/interaction patterns (tab bars, stack nav, touch targets) that differ from the web app.
- A generated mobile app icon / splash screen when the existing web source only has a small favicon or no usable high-res equivalent -- as long as the generated asset uses the existing app's brand colors, typography, and visual style. Generating a brand-matching icon is fine; the anti-pattern is a generic/off-brand one.
- `pnpm dev` / `pnpm run dev` failing at workspace root. Replit apps run via workflows (`restart_workflow`), not root-level pnpm dev.
- Unused scaffold files (e.g., default `src/components/ui/*.tsx` shadcn components that came with `createArtifact`, default `favicon.svg`). These are scaffold-provided, not agent-added slop. Focus only on files the agent actually wrote or changed.

DO flag (these are real regressions):
- Content images and logos NOT copied from the existing app when equivalents exist there (e.g. the web app has `public/logo.png` but the mobile uses a different logo with different colors/shapes).
- Placeholder/stock/AI-generated assets that break brand cohesion -- wrong colors, generic illustrations, Ionicons used as the app logo when the existing app has a custom brand mark.
- New colors or fonts invented for the mobile app when the existing app has a defined palette/typography.
- Empty states or placeholder content instead of the real data the existing app shows.

Focus on: does the new app run (via workflows)? Does it do what the user asked? Does it *look like the same product* as the existing app (brand, colors, images, fonts)?
```

For non-mobile follow-ups (slides, video, auth, etc.), keep the same structure but adapt:

- **Artifact type** + create step (e.g. `artifactType: "slides"` or `"video-js"`).
- **Done criteria** to match the target (e.g. slides: "Deck opens, all slides render"; video-js: "Video plays from start to end").
- **Brand/visual reuse** still applies when the artifact has a visual surface (slides, video-js). For headless follow-ups (auth, data-visualization that runs in an existing app), drop those bullets.
- Do not add a CodeExecution deploy-suggestion step. Publishing suggestions are handled by the main agent calling `SuggestUserAction({ action: "deploy", message: "The app is ready to publish." })`, not by task-plan callback code.
- **Reviewer note**: keep the "don't reject for missing workspace hooks / subjective component reuse / platform-native patterns" parts; update the "DO flag" list to match the actual brand/content expectations of the target type.

**Step 2: Call `proposeMigration`.** Reference each plan file by path:

- If you have a `propose_migration` tool: call it directly.
- If you have code execution: call `proposeMigration` from the sandbox:

```javascript
const result = await proposeMigration({
  actionLabel: "Update project to create mobile app",
  message: "I need to update your project structure so it can support multiple apps. This may take a couple of minutes. Approve to continue.",
  migrationTask: {
    title: "Port existing restaurant website",
    filePath: ".local/tasks/port-restaurant-website.md"
  },
  followUpTasks: [
    {
      title: "Build mobile app",
      filePath: ".local/tasks/build-mobile-app.md"
    }
  ]
});
```

**`actionLabel`** and **`message`** are user-facing -- keep them friendly and non-technical.

**`migrationTask`** is required. It's the port task -- moving the existing app into the new workspace structure.

**`followUpTasks`** is optional. Include one entry for each piece of work the user asked for after migration. You can include zero, one, or multiple follow-up tasks. Omit it entirely if the user only asked for the migration itself.

**Before doing any work**, tell the user the plan in their own language. Use simple, non-technical words:

> **This will happen in 2 steps:**
>
> **Step 1** -- I'll move your existing app into a new structure. It will look and work exactly the same.
>
> **Step 2** -- Once that's confirmed working, I'll build [describe what they asked for].
>
> I'll check in with you after Step 1 before moving on.

## If you are a background task agent

Your task description contains the full plan and instructions for your specific task. Follow them.

- If your task is the migration phase, read the referenced `port-existing.md` file, port the existing app, ask the user to verify it, and then call `markTaskComplete({ task_ref: "<your assigned task ref>", ... })` as the final callback in CodeExecution.
- If your task is a follow-up task, the project is already migrated -- do not rerun migration. Follow the plan in your task description.
- Use the helper scripts and stack-specific instructions from the referenced task files when they are available.

Keep the user updated in simple, non-technical language while you work.
