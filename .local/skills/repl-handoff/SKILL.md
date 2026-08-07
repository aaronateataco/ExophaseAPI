---
name: repl-handoff
description: Offer to move this conversation into a Repl, or to create a separate Repl for a different piece of work.
---

# Repl Handoff

This conversation's sandbox is temporary — there is no persistent Repl the
user owns, deploys, or returns to. When the work deserves one, offer the
user one of two things:

- **`transitionToRepl`** — continue *this* conversation in a Repl. Everything
  discussed comes along.
- **`createNewRepl`** — start a *separate* Repl for a different piece of
  work. This conversation continues.

Both post a card the user must confirm. Nothing happens until they do.

Offer, don't insist. If the user declines, keep helping them here and don't
re-offer unless they bring it up again.

## Stack templates

When your instructions mention workspace stack templates, either function
accepts an optional `templateReplId` naming the template the new Repl
should start from. Short template lists appear inline in your
instructions; when the workspace curates more than fit there, call
`listTemplates({})` first to see every template's ID, title, and
description. Pass a `templateReplId` only when it clearly fits what the
user wants to build; omit it for the standard blank setup. IDs must come
from the list — anything else is rejected. Your pick is a suggestion: the
user can change or clear the template on the confirmation card, and you
will be told what they chose.

## Available Functions

### listTemplates()

List the workspace's curated stack templates: each entry's `replId` (what
`templateReplId` takes), title, and description. Use it when your
instructions point here instead of inlining the list, or when you need to
re-check what a template is before recommending it. Returns
`{ available: false }` when no list could be fetched this turn — offer
the standard setup in that case.

```javascript
await listTemplates({});
```

### transitionToRepl({ templateReplId? })

Offer to continue this conversation inside a Repl. The offer is always
about the current conversation, and its context comes along automatically;
the only argument is the optional stack template above.

Use when the user wants to build the thing you have been discussing, and
the discussion so far is the context that matters.

**Ends your turn.** The user decides before anything else happens, so say
what you need to say before calling it.

```javascript
await transitionToRepl({});
```

### createNewRepl({ prompt, title, templateReplId? })

Offer to create a separate Repl and hand the work to the agent there.

Use when the work is a distinct project rather than a continuation — the
user asks for something adjacent, or wants several things built
independently.

- `prompt` — what the agent in the new Repl should do. Write it for an
  agent that has not seen this conversation: state the goal and any
  decisions already made. Don't reference "what we discussed".
- `title` — a few words naming the Repl. Also the basis for its slug.
- `templateReplId` (optional) — a workspace stack template from the list in
  your instructions (see "Stack templates" above).

**Does not end your turn**, so you can offer several Repls in one go when
the user asks for several things.

The user can edit every field before confirming, so treat none of them as
final until their response arrives. If they change something, you will be
told what they changed it from — take the correction as a signal about how
they want the work framed.

```javascript
await createNewRepl({
  title: 'Invoice parser',
  prompt:
    'Build a Python CLI that reads PDF invoices from a folder and writes ' +
    'a CSV of vendor, date, and total. Use pdfplumber for extraction.',
});
```
