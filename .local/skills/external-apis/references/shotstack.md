# Shotstack

Proxy requests to Shotstack via Replit-managed billing.

## Callback

Use `externalApi__shotstack` in `codeExecution`.

## Allowed operations

- `POST` `/edit/v1{/templates}?/render` - Submit a Shotstack render job (ad-hoc timeline or template-bound; bills on polled output duration for video/audio, flat per render for images).
- `GET` `/edit/v1/render/:id` - Poll a Shotstack render job for status and final duration (used by the billed render op to settle cost; not billed separately).
- `POST` | `GET` | `PUT` | `DELETE` `/edit/v1/templates{/:id}?` - Shotstack template CRUD: create (POST /edit/v1/templates), list (GET /edit/v1/templates), fetch (GET /edit/v1/templates/{id}), update (PUT /edit/v1/templates/{id}), delete (DELETE /edit/v1/templates/{id}). No charge — billed on render.
- `GET` `/edit/v1/probe/:url` - Inspect media metadata via FFprobe (GET /edit/v1/probe/{url-encoded-url}). No charge — utility endpoint, not on the Shotstack pricing page.
- `POST` | `GET` | `DELETE` `/serve/v1/assets{/render}?{/:id}?` - Shotstack Serve API: transfer (POST /serve/v1/assets), fetch (GET /serve/v1/assets/{id}), delete (DELETE /serve/v1/assets/{id}), list by render (GET /serve/v1/assets/render/{id}). No charge — see storage/bandwidth note above.
- `POST` | `GET` | `DELETE` `/ingest/v1/sources{/upload}?{/:id}?` - Shotstack Ingest API: ingest from URL (POST /ingest/v1/sources), direct upload (POST /ingest/v1/sources/upload), list (GET /ingest/v1/sources), fetch (GET /ingest/v1/sources/{id}), delete (DELETE /ingest/v1/sources/{id}). No charge — see storage/bandwidth note above.

Authorization is handled automatically by Replit. Do not pass an `Authorization` header.

## Skill

## Shotstack quickstart

Render videos, images, and audio from a JSON timeline through
Shotstack passthrough billing. Submit a render, poll its status,
then download the finished file. Send the edit as an object in
`body` (it is serialized for you — do not pre-stringify).

```javascript
const submit = await externalApi__shotstack({
  path: '/edit/v1/render',
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: {
    timeline: {
      tracks: [
        {clips: [{asset: {type: 'text', text: 'Hello from Replit'}, start: 0, length: 5}]},
      ],
    },
    output: {format: 'mp4', resolution: 'sd'},
  },
})

const renderId = submit.body.response.id
let url
for (let attempt = 0; attempt < 60; attempt++) {
  await new Promise((resolve) => setTimeout(resolve, 5000))
  const status = await externalApi__shotstack({
    path: '/edit/v1/render/' + renderId,
    method: 'GET',
  })
  if (status.body.response.status === 'done') {
    url = status.body.response.url
    break
  }
  if (status.body.response.status === 'failed') throw new Error('Shotstack render failed')
}

console.log(url)
```

Authorization is managed by passthrough billing. Do not set an
`Authorization` header manually.
