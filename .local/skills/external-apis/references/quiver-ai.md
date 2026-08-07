# QuiverAI

Proxy requests to QuiverAI via Replit-managed billing.

## Callback

Use `externalApi__quiver_ai` in `codeExecution`.

## Allowed operations

- `POST` `/svgs/generations` - Generate SVGs from a text prompt (JSON or SSE response).
- `POST` `/svgs/vectorizations` - Vectorize a raster image to SVG (JSON or SSE response).
- `GET` `/models{/:model_id}?` - List models or fetch a single model.

Authorization is handled automatically by Replit. Do not pass an `Authorization` header.

## Skill

## QuiverAI quickstart

Generate SVG icons and illustrations from a text prompt through
QuiverAI passthrough billing. Send the required fields as an
object in `body` (it is serialized for you — do not
pre-stringify). Supported models: `arrow-1`, `arrow-1.1`,
`arrow-1.1-max`.

```javascript
const result = await externalApi__quiver_ai({
  path: '/svgs/generations',
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: {model: 'arrow-1.1', prompt: 'a minimalist unicorn icon'},
})

const svg = result.body.data?.[0]?.svg

// File writes and imports are impure — keep them inside the
// "use impure" boundary; pass the (serializable) SVG markup in.
await (async function (markup, out) {
  "use impure";
  const fs = await import('node:fs/promises')
  await fs.mkdir('attached_assets', {recursive: true})
  await fs.writeFile(out, markup)
})(svg, 'attached_assets/icon.svg')
```

To vectorize an existing raster image to SVG, POST to
`/svgs/vectorizations` with `body: {model, image: {url}}`. Both
endpoints return the SVG markup at `body.data[0].svg`.
Authorization is managed by passthrough billing. Do not set an
`Authorization` header manually.

## Example

```javascript
const result = await externalApi__quiver_ai({
  path: '/svgs/generations',
  method: 'POST',
  body: {},
})

console.log(result.status)
console.log(result.body)
```
