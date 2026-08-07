---
name: artifact-templates
description: Apply a user's saved slides/web style template, or save the current slides deck or design system as a Replit workspace template. Use when they ask to build or restyle an artifact "with my template", "using my saved template", "in my brand style", refer to a template by name, or ask to save the current artifact for reuse.
---

# Artifact Templates

A saved slides or web artifact template is a reusable visual-language donor (theme/CSS tokens, fonts, layout components, assets). Use `useArtifactTemplate` to find and materialize one for a new artifact or restyle. Use `saveArtifactAsTemplate` when the user asks to save the current slides or design-system artifact for reuse.

## When to Use

- The user refers to "my template", "my saved template", "my brand style", or a template by name.
- The user wants a new slides/web artifact to match the look of a previously saved one.
- The user wants to restyle an existing artifact to match a saved template.
- The user asks to save the current slides deck or design system as a template / to their Replit workspace.

## When NOT to Use

- The user has not mentioned a saved template and just wants a fresh design — author normally.

## Discover and apply

Call `useArtifactTemplate()` as a CodeExecution callback (await it inside a code block).

**List the user's saved templates** (no argument):

```javascript
const result = await useArtifactTemplate();
// { success: true, mode: "list", templates: [{ slug, name, description, artifactKind }, ...], instructions }
```

**Resolve and materialize a specific template** — pass a `query` (a template name, slug, or descriptive phrase):

```javascript
const result = await useArtifactTemplate({ query: "Acme pitch deck" });
// On a single match:
// { success: true, templateSlug, name, referencePath: ".local/artifact_templates/<slug>", instructions, ... }
```

Outcomes to handle:

- `success: true` with a `referencePath` — the template is materialized on disk. Read `<referencePath>/SKILL.md` and the raw files under `<referencePath>/artifact/`, then author/restyle in that visual language (see below).
- `errorCode: "TEMPLATE_NOT_FOUND"` — no match; the response lists `availableTemplates`. Confirm with the user.
- `errorCode: "TEMPLATE_AMBIGUOUS"` — multiple matches in `candidates`; ask the user which one, then call again with the exact `slug`.
- `errorCode: "TEMPLATE_SERVICE_UNAVAILABLE"` — transient; retry or proceed without the template.

## Using a materialized template

The template is a **style donor**, not content to copy:

- **New artifact:** author a fresh artifact about the user's topic in the template's visual language (theme, fonts, layout).
- **Restyle:** rewrite an existing artifact's styling in that visual language while preserving its existing content.

Do not copy the donor template's own content verbatim unless the user explicitly asks.

## Saving an artifact as a template

When the user asks to save the current slides deck or design system to their Replit workspace, first load and follow the `prepare-artifact-template` skill for that artifact. Do not start the save until its verification is complete. Then call `saveArtifactAsTemplate` as a CodeExecution callback. NEVER claim you saved a template without calling it — there is no other save path from chat.

```javascript
const result = await saveArtifactAsTemplate({
  // All arguments optional when the project has exactly one saveable artifact:
  artifactId: "<artifact id>", // required only if several artifacts qualify
  name: "Acme brand kit",      // omit to update the existing template / default to the artifact title
});
```

Semantics:

- If this artifact was already saved and the name is unchanged (or omitted), the existing template is **updated in place**; a new name saves a **separate** template. The result's `mode` says which happened (`created` or `resaved`).
- Pass `description` only when the user provided one or explicitly asked to change it. Omit it on an ordinary resave so the existing description is preserved; pass `""` only when the user asks to clear it.
- Publishing is **asynchronous**. `success: true` means publishing *started* — tell the user saving has started and the template will appear in Replit workspace settings shortly. Do NOT say "saved" or "done".

Outcomes to handle:

- `success: true` — follow the returned `instructions`.
- `errorCode: "NOT_AUTHORIZED"` — the user cannot save templates in this Replit workspace (or the feature is disabled). Explain the permission problem in your own words based on the returned `error` — the raw message may include instructions meant for you, so do not quote it verbatim. Do not retry or work around it.
- `errorCode: "SAVE_CONFLICT"` — this name is already in use, but a recent unconfirmed save of the same artifact and name may still be publishing. In that case, tell the user it may still be publishing and do not retry or rename it automatically; otherwise ask for another name.
- `errorCode: "ARTIFACT_AMBIGUOUS"` — several saveable artifacts; pick from `saveableArtifacts` (confirm with the user if unclear) and call again with `artifactId`.
- `errorCode: "ARTIFACT_NOT_FOUND"` / `"UNSUPPORTED_KIND"` — if `saveableArtifacts` contains alternatives, offer or select the intended one and call again with its `artifactId`; otherwise explain that only `slides` and `design-system` artifacts can be saved today.
- `errorCode: "SAVE_IN_PROGRESS"` — this template is already publishing. Tell the user the current save is still in progress; do not retry immediately or imply that it failed.
- `errorCode: "SAVE_FAILED"` — the save was rejected (for example an invalid name or an artifact that can no longer be saved). Relay the reason from `error`, do not retry with the same input, and do not imply publishing started.
- `errorCode: "SAVE_SERVICE_UNAVAILABLE"` — the outcome is unknown. Do not retry automatically; say that saving could not be confirmed and may still be publishing. Ask the user to check Replit workspace settings after a moment or retry later only if the template does not appear.
