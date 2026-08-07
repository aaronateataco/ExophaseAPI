# Browserbase

Proxy requests to Browserbase via Replit-managed billing.

## Callback

Use `externalApi__browserbase` in `codeExecution`.

## Allowed operations

- `POST` `/v1/fetch` - Fetch a URL via a managed headless browser. Billed per call; rate depends on the `proxies` flag and whether `format` selects Fetch Extract (markdown/json) vs normal Fetch (raw).
- `POST` `/v1/search` - Web Search (Open Web Tools) — flat per-call rate; numResults (1–25) does not affect price.
- `POST` `/v1/sessions` - Create a browser session. Billed by Browser Minute + Proxy MB observed via polling GET /v1/sessions/{id} until terminal status or expiresAt passes.
- `POST` `/v1/sessions:id(/[^/]+)` - Close a browser session (REQUEST_RELEASE). No charge — session duration is billed on creation.
- `POST` | `GET` | `DELETE` `/v1/contexts/:path*` - Browserbase contexts: create (POST /v1/contexts), read (GET /v1/contexts/{id}), delete (DELETE /v1/contexts/{id}). No charge.

Authorization is handled automatically by Replit. Do not pass an `Authorization` header.

## Skill

## Browserbase quickstart

Web search and managed-browser page fetches through Browserbase
passthrough billing. Send the required fields as an object in
`body` (it is serialized for you — do not pre-stringify).

```javascript
const search = await externalApi__browserbase({
  path: '/v1/search',
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: {query: 'replit deployments', numResults: 5},
})

const top = search.body.results?.[0]
if (top) console.log(top.title, top.url)

const page = await externalApi__browserbase({
  path: '/v1/fetch',
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: {url: 'https://docs.replit.com', format: 'markdown'},
})

console.log(page.body.content)
```

`/v1/search` returns ranked results under `body.results`;
`/v1/fetch` returns the page body as a string in `body.content`.
Authorization is managed by passthrough billing. Do not set an
`Authorization` header manually.

Each search and fetch is billed and adds latency. Fetch only the
few most relevant URLs rather than every search result.

## Example

```javascript
const result = await externalApi__browserbase({
  path: '/v1/fetch',
  method: 'POST',
  body: {},
})

console.log(result.status)
console.log(result.body)
```
