---
name: clerk-auth
description: "User authentication via a Replit-managed Clerk tenant. Default solution for user authentication; prefer the replit-auth skill only when the user explicitly asks for Replit Auth / Replit SSO / \"Sign in with Replit\". Load whenever Clerk appears in the conversation or codebase — even if it's unclear whether the project uses Replit-managed or external Clerk; the skill detects and routes accordingly. Also load for enterprise SSO or external identity-provider connection questions, including Okta Workforce, Microsoft Entra ID / Azure AD, Google Workspace SAML, custom SAML, OIDC, and EASIE, unless the user explicitly says the app uses a non-Clerk authentication system. Prefer recall over precision. Do not rely on generic Clerk knowledge or send the user to dashboard.clerk.com without loading this skill — Replit-managed Clerk is configured very differently from external Clerk. Example use cases include: setup, customization (login providers, branding such as 'continue with <app_name>' on the Google login page, email verification), key configuration, feature or pricing questions, troubleshooting, and migrations to or from Replit Auth. When asked to roll back or revert a Clerk migration, you must load the replit-auth skill."
---

# Clerk Auth

## Overview

Clerk Auth gives the user's app its own dedicated authentication system, powered by a Replit-provisioned Clerk tenant. End users sign up in the app and the builder gets full control over branding and login methods.
- **Replit-managed**: Replit provisions the Clerk tenants and key automatically. No need to touch accounts/secrets manually; `checkClerkManagementStatus` reports whether the current user can open the Clerk dashboard.
- **Two isolated environments**: Development and Production have separate user stores — accounts/data do not cross over. Test keys are used during development and automatically swapped to live keys when the app is published.

  **Expected during development — do NOT treat as a problem and do NOT try to "fix" it:**
  - A `pk_test` Clerk publishable key in `.replit` config or environment
  - Console logs that say things like "Clerk has been loaded with development keys" or otherwise warn about development keys
- **Login methods**: email/password (with email verification) and SSO via Google, GitHub, Apple, and X; custom OAuth credentials supported in Production for branded consent screens
- **Managed from the Auth pane**: user management and consent screen configuration managed from the builtin Auth pane
- **Not supported today**: SMS/phone sign-in, organization tenants
- **Configured in the Clerk dashboard when authorized, not in code**: MFA/2FA, session length, password breach checks, embedded/native webview sign-in, email sender name — see "Intent: Dashboard-side settings" below

## When to Use

- User wants authentication, login, signup, or user accounts (this is the default)
- User wants custom branding on login/signup screens
- User wants their own user database
- Any generic auth request that does not explicitly mention "Replit Auth", "Sign in with Replit", or "Replit SSO"

## Step 1: Check Clerk Management Status

ALWAYS call `checkClerkManagementStatus` before taking any action. This indicates if the user's secrets point to Replit-managed Clerk, external Clerk, or no Clerk setup. It also returns `dashboardAccess` for the current user.

```javascript
const status = await checkClerkManagementStatus();
console.log(status);
```

Then browse the user's code briefly to get a full picture of the user's setup (to see if the code actually uses their secrets).

Failing to do so can cause extreme user confusion and lead the user to get into a bad state with their app. DO NOT proceed with steps 2 and 3 until you have done step 1 and know what the user currently has / what they want.

## Step 2: Route Based on Status

**`external`**: The user is managing their own Clerk instance. This skill only applies if the user is asking to migrate them to Replit-managed Clerk.

**`unknown`**: DO NOT proceed to Step 3. Ask the user: "Are you using Replit-managed Clerk (set up automatically) or your own external Clerk account? Check if the Clerk publishable key stored in secrets matches your own personal Clerk account. If so, it is external." DO NOT say anything more than just this question.

**`not_configured`**: Neither Replit-managed or external Clerk has been set up — continue to step 3.

**`managed`**: Replit-managed Clerk already set up — continue to step 3.

## Step 3: Route Based on Request Type

IMPORTANT: DO NOT start this step if the management status you found was unknown or external.

Identify the user's intent and follow the matching section below.

### Intent: Inquiry, Configuration, Login Providers, and Setup Questions

The user is asking a factual or conceptual question about Clerk Auth (how something works, whether a feature is supported, pricing, setup requirements, configuration options, environment behavior, etc.) or is asking you to change their login providers, OAuth credentials, or consent screen branding. Do not match on this section if the user is asking you about build/setup, migration, troubleshooting, etc.

If you match on this section, call `searchReplitDocs` first — do not answer from prior knowledge.

```javascript
const result = await searchReplitDocs({ query: "<query>" });
console.log(result.response);
```

Common question categories and example queries:

Enterprise SSO connection requests include Okta Workforce, Microsoft Entra ID (formerly Azure AD), Google Workspace SAML, custom SAML, OpenID Connect (OIDC), and EASIE. Route them by management status:

- **`managed`**: Follow **Intent: Dashboard-side settings** below. Do not call `searchReplitDocs`.
- **`not_configured`**: Do not emit a dashboard marker because there is no Clerk app to manage. If the user asks you to add or configure enterprise SSO, follow **Intent: Implementation & Changes** to set up Clerk first. If the user asks only how enterprise SSO works, explain that Clerk Auth must be set up first and ask whether they want you to set it up, then stop.

- **Login providers, OAuth credentials, social SSO providers (Google, GitHub, Apple, and X), consent screen branding, or Auth pane questions**
  - Example question: "How do I add Apple login?"
  - Example query: `"Configure custom <provider_name> OAuth credentials for Clerk Auth"`
  - After the search, direct the user to the **Auth pane** in the workspace toolbar.
- **Clerk DNS, custom domain, email verification, DKIM, or SPF setup questions**
  - Example question: "How do I set up Clerk DNS for email verification?"
  - Example query: `"Set up Clerk DNS for email verification"`
- **Clerk Auth feature support (e.g. organizations, passkeys, magic links, webhooks)**
  - Example question: "Does Clerk Auth support passkeys?"
  - Example query: `"Does Clerk Auth support <feature>"`
- **Clerk Auth pricing, MAU limits, quotas, or plan tier questions**
  - Example question: "Does Clerk Auth have a MAU limit?"
  - Example query: `"Clerk Auth MAU limit and pricing"`
- **Live vs test keys (`pk_test` / `sk_test` vs `pk_live` / `sk_live`)**
  - Example question: "My Clerk publishable key starts with `pk_test` — how do I switch to a live key?"
  - Example query: `"Clerk Auth test vs live keys for development and production"`
- **Sign-in, sign-up, or user management questions (e.g. missing accounts or data)**
  - Example question: "Why can't I sign in to my published app with the account I made during development?"
  - Example query: `"Clerk Auth development vs production environment user separation"`

### Intent: Dashboard-side settings

Some auth settings for Replit-managed Clerk are not configurable in code or the Auth pane — they live in the Clerk dashboard for the app's Clerk instance. Requirements: management status is `managed` (Step 1). Do NOT attempt any code changes for these settings, and do not link raw dashboard.clerk.com URLs — the button tag below is the only sanctioned path into the Clerk dashboard for managed apps.

Route by the `dashboardAccess` value returned in Step 1:

- **`authorized`**: Continue with the matching table row or dashboard-home fallback below.
- **`requires_personal_pro`**: Tell the user plainly that this request requires an active personal Replit Pro subscription. Do not give dashboard steps, emit an `<open-in-pane>` marker, mention a button, or link to a payments page or raw dashboard.clerk.com URL. Then stop.
- **`unavailable`**: Tell the user plainly that Clerk dashboard access is unavailable to them for this app. Do not give dashboard steps, emit an `<open-in-pane>` marker, mention a button, or link to raw dashboard.clerk.com URLs. Then stop.
- **`unknown`**: Tell the user plainly that you could not check Clerk dashboard access. Ask them to try again shortly. Do not give dashboard steps, emit an `<open-in-pane>` marker, mention a button, or link to raw dashboard.clerk.com URLs. Then stop.

Only continue below when `dashboardAccess` is `authorized`.

| Setting | Example user requests | Marker to emit | Dashboard steps to give |
| --- | --- | --- | --- |
| Password breach check (HIBP) | "users can't pick a password, it keeps reporting security breaches" / "disable the password breach check" | `<open-in-pane tool="clerkDashboard/passwordSettings"></open-in-pane>` | Configure → User & authentication → Password tab → Update password requirements → adjust "Reject compromised passwords" → Save |
| Session length | "users are signed out every time they close the app — keep sessions open for 30 days" | `<open-in-pane tool="clerkDashboard/sessions"></open-in-pane>` | Configure → Sessions → adjust inactivity/maximum lifetime → Save |
| MFA / 2FA | "how do I turn on 2FA/MFA for my app's users?" | `<open-in-pane tool="clerkDashboard/multiFactor"></open-in-pane>` | Configure → User & authentication → Multi-factor → enable methods (e.g. Authenticator application, Backup codes) → Save |
| Enterprise SSO connections | "What would it take to add enterprise SSO with Okta?" / "How do I configure Microsoft Entra ID?" / "How do I add a custom SAML provider?" / "How do I set up Google Workspace SAML?" / "How do I configure OIDC or EASIE?" | `<open-in-pane tool="clerkDashboard/enterpriseSsoConnections"></open-in-pane>` | Configure → User & authentication → SSO connections → Add/edit connection → Save |
| Embedded webview sign-in | "sign-in doesn't work inside my mobile/embedded webview" | `<open-in-pane tool="clerkDashboard/nativeApplications"></open-in-pane>` | Configure → Developers → Native applications → configure the native/webview application settings |
| Email sender name | "change the sender name on verification emails — it's not in my code" | `<open-in-pane tool="clerkDashboard/emailCustomization"></open-in-pane>` | Configure → Customization → Emails → edit the sender/email template settings → Save |

### Fallback: Other dashboard-side settings

Use the dashboard-home fallback only when all of these conditions are true:

1. The management status is `managed`.
2. `dashboardAccess` is `authorized`.
3. The user asks to administer Replit-managed Clerk in the Clerk dashboard, not in code or the Auth pane.
4. No table row above has a specific dashboard destination for the request.

Do not use this fallback for implementation, troubleshooting, documentation, feature-support, pricing, login-provider, or Auth pane requests. Do not use it for another authentication provider. Do not use it when the management status is `external`, `unknown`, or `not_configured`.

Tell the user that the setting is in the Clerk dashboard. Give dashboard navigation steps only when you know them. Do not guess a dashboard location. Replit-managed Clerk has separate Development and Production instances. Use the environment switcher at the top of the Clerk dashboard to select the instance for this change. End the reply with this marker on its own line:

```
<open-in-pane tool="clerkDashboard"></open-in-pane>
```

How to answer a table-row request:

1. Tell the user plainly that this is a setting in the Clerk dashboard (which Replit manages for them), not something in their code.
2. Give the numbered dashboard steps from the table row.
3. End your reply with the full marker from the table on its own line (the complete `<open-in-pane …>` element — a bare tool value renders as plain text) — it is replaced by an "Open in Clerk Dashboard" button that signs the user in and lands directly on that settings page.

Choosing the environment for a table-row request — go ONLY by what the user's request says, never by guessing deployment state:

- Default (the request does not mention an environment): emit the marker exactly as in the table — it opens the **Development** instance. ALWAYS end your prose with one sentence telling the user that this change applies to their Development instance, and that they can apply it to their published app by switching to Production with the environment switcher at the top of the Clerk dashboard.
- The user explicitly mentions development ("in dev", "my development environment"): emit the default marker. Do not mention the environment switcher.
- The user explicitly mentions production ("my live app", "in production", "the published site"): prefix the setting inside the marker with `prod`, e.g. `<open-in-pane tool="clerkDashboard/prod/sessions"></open-in-pane>`. Do not mention the environment switcher.

Example ending for an MFA request:

```
<open-in-pane tool="clerkDashboard/multiFactor"></open-in-pane>
```

Do not mention a button, tag, or marker in your prose. Keep the reply to the plain statement plus the numbered steps (and the environment-switcher sentence when applicable).
### Intent: Implementation & Changes

The user wants to set up Clerk, integrate it into their code, or customize the sign-in page. Read `.local/skills/clerk-auth/references/setup-and-customization.md` for guidance.

### Intent: Troubleshooting

The user reports that Clerk Auth is broken, misbehaving, or not doing what they expect, or handling Clerk-related errors surfaced in the console logs while addressing the user's requests. Re-load the clerk-auth skill before reading the references — even if it is already open in this conversation — so you pick up the latest canonical snippets, then read **both** of the following together before taking any action:

1. `.local/skills/clerk-auth/references/troubleshoot.md` — generic troubleshooting guidance.
2. `.local/skills/clerk-auth/references/setup-and-customization.md` — the ground-truth guidance for Replit-managed Clerk setup and coding.

Example user inputs:

- "The preview / app / homepage isn't loading" (when Clerk is used)
- "Failed to load Clerk JS"
- "Auth is broken" / "login doesn't work" / "I cannot login"

### Intent: Migrating from Replit Auth

Clerk migrations run as an isolated background task so they are merge-gated and never run inline in this conversation.

**Step 1: Create the migration plan file.** The migration playbook is the same across every project — the canonical rubric in `.local/skills/clerk-auth/references/task/migrate.md` already has the full Steps 1-5 content (provisioning, user data, code, restart, self-test). **Copy it** into `.local/tasks/` instead of paraphrasing:

```bash
mkdir -p .local/tasks
cp .local/skills/clerk-auth/references/task/migrate.md .local/tasks/migrate-to-clerk.md
```

Do NOT rewrite the steps. The rubric is the contract.

**Step 2: Call `proposeClerkMigration`** (via `code_execution`) referencing that plan file:

```javascript
await proposeClerkMigration({
  actionLabel: "Migrate to Clerk",
  message: "Migrating from Replit Auth to Clerk will create a new Clerk app, copy over your Replit Auth users, and update your application code to use Clerk.",
  migrationTask: {
    title: "Migrate from Replit Auth to Clerk",
    filePath: ".local/tasks/migrate-to-clerk.md",
  },
});
```

Then stop. The migration runs in an isolated background task after the user approves, and the diff is review-gated before it merges. Read `.local/skills/clerk-auth/references/troubleshoot.md` upfront for context in case breakage surfaces.

### Intent: Reverting a Clerk Migration (Back to Replit Auth)

You MUST load the `replit-auth` skill — it contains the full rollback procedure.

