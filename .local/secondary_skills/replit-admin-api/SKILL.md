---
name: replit-admin-api
description: Call the Replit Admin API (api.replit.com/v1). Use when building or changing Enterprise account analytics or administration, including usage and cost dashboards, directories, deployments, and budget controls.
---

# Replit Admin API

Base URL `https://api.replit.com/v1`. Auth: `Authorization: Bearer <key>` — keep the key in an environment variable (e.g. `REPLIT_API_KEY`), never in code. To get a key, the user goes to **Replit account Settings → Developer tab**; API keys there are only available to **account admins**, so a non-admin must ask an admin of their Enterprise account to generate one. All operations are scoped to the key's Account. Full contract: fetch `https://api.replit.com/openapi.json` — consult it when designing any request, response type, or error path.

## Endpoints

| Method and path | Scope | Purpose and key parameters |
|-----------------|-------|----------------------------|
| `GET /account/summary` | `read:*` | Account metadata, seat counts, workspaces, SCIM state, and administrative settings. Cost data comes from `/usage`. |
| `GET /workspaces` | `read:*` | Account workspace directory. Filter with `search`. |
| `GET /workspaces/{workspaceId}` | `read:*` | One Account-owned workspace. |
| `GET /members` | `read:*` | Account member directory. Filter with `workspaceId`, `role`, and `search`. |
| `GET /groups` | `read:*` | Workspace groups. Filter with `workspaceId`. |
| `GET /groups/{groupId}/users` | `read:*` | Active users in one group. Missing, hidden, deleted, and cross-Account groups return `404`. |
| `GET /usage` | `read:*` | Cost and usage. `groupBy` is `member`, `project`, `workspace`, or `timeseries`; `granularity=day` is valid only with `timeseries`. Filter with `workspaceId`, `groupId`, `userId`, `projectId`, range parameters, and repeated `type` values. |
| `GET /projects` | `read:*` | Account projects. Filter with `workspaceId`, `search`, and `hasDeployment`; deployment state is eventually consistent. |
| `GET /deployments` | `read:*` | Deployments in a required `workspaceId`. Filter with `projectId` and `status`. |
| `GET /deployments/{deploymentId}` | `read:*` | One deployment owned by an Account workspace. Missing and inaccessible deployments return the same `404`. |
| `GET /budgets` | `read:*` | Account spending controls and Workspace, group, and member Agent limits. Filter with `workspaceId` and `type`. |
| `POST /budgets` | `write:budgets` | Set, replace, or clear one budget or limit. It is desired-state and repeating an identical request is idempotent. Validate the request against the OpenAPI `budget-update` schema. |

All list endpoints use `limit` (default 50, maximum 100) and `cursor`. Their responses return `pagination.cursor` and `pagination.hasMore`. `/usage` differs: it paginates `groups[]` and returns `data.pagination.nextCursor`.

## The rate budget

Every endpoint shares an account-wide quota of 300 requests/minute and 10,000 requests/hour. `/usage` also consumes a 100 requests/minute usage quota. The rate-limit headers report the most constrained applicable quota. Apply the same retry, pacing, and concurrency controls to budget writes as to reads.

- Route **every** `/usage` call through one **serial queue** with priorities (high = interactive request, low = background build). Pace it with `X-RateLimit-Remaining` / `X-RateLimit-Reset` and retry 429s honoring `Retry-After`.
- Coordinate directory pagination with the same account-wide budget. Do not treat directory endpoints as unbounded.
- Per-entity daily series require one `/usage` call each, so build them progressively: low-priority background fetches, partial responses carrying `isComplete` and a pending count, and client polling until complete.

## Usage data semantics

Grouped results return `groups[]`: `key` (userId/projectId/workspaceId/date), `totalCostUsd`, and `metrics[]`. Metrics contain public `id`, customer-facing `name`, `category`, nullable `usage` and `usageUnit`, and `costUsd`. Filter metrics with the repeatable `type` query parameter; do not use internal billing identifiers.

- Entity groups (`member`, `project`, and `workspace`) arrive **ordered by descending `totalCostUsd`**, so capped pagination keeps the top spenders. Timeseries groups arrive in ascending date order; paginate the full series before drawing conclusions from it.
- Capped entity pagination creates a **blind spot**: on a ~9k-project account, 5 pages (500 groups) hid everything under $20; 20 pages (2000 groups) shrank the blind spot to under $1. When a feature claims something has *zero* cost, fetch deep enough, compute the **capture threshold** (smallest positive cost fetched), return it from your API, and disclose it in the UI ("costs below $X may not be captured"). A zero-cost claim is complete only when the threshold is exposed alongside it.
- Zero-spend members are absent from `groupBy=member` results — join against `/members` to include them.
- Per-entity daily series cost one `/usage` call each (`groupBy=timeseries`, `granularity=day`, plus the entity filter); there is no bulk endpoint.
- Some group projectIds refer to deleted projects and miss on join against `/projects` — treat joins as optional.
- Usage pagination: pass `data.pagination.nextCursor` as `cursor` on the next request and stop when it is null. Cap `maxPages` and **log a warning on truncation** — the blind spot must be visible in logs, since it is invisible in the data.

## Caching

Fresh data costs minutes of rate-limited calls, so every interactive app needs a cache. Two tiers:

**In-memory** — the default for a single-server app. Cache promises keyed by `endpoint:range`; usage TTL ~10 min, directory ~15 min. **Warm up** the default range at server startup so first loads are instant. Restarts start cold, and repopulation is rate-limit bound (minutes) — acceptable when the app tolerates a progressive fill after restart.

**Database-backed** — choose when restarts/redeploys must keep warm data. Persist the cache in any SQL database:

- Schema: `api_cache(key text primary key, payload jsonb, fetched_at timestamptz)` with the same `endpoint:groupBy:days` keys; plus a per-entity daily table (`entity_id, date, cost_usd, fetched_at`) so a partially-built daily matrix survives restarts and **resumes** — on boot, load persisted rows and fetch only missing or stale entities.
- Read path: serve from DB within TTL; refresh stale entries in the background (stale-while-revalidate) so requests stay fast.
- Write path: upstream fetches still go through the serial queue — the DB is a cache layer under the same rate budget.
- If dev and production use separate databases, production boots cold — keep the warm-up logic.

## Proven architecture

A practical architecture uses a thin backend proxy in front of the Admin API (browser clients can't call it directly — the key must stay server-side), an OpenAPI contract for your own `/api`, generated typed client hooks, the serial usage queue, in-memory caches with startup warm-up, and a progressive background builder for per-member daily series with client polling until `isComplete`.
