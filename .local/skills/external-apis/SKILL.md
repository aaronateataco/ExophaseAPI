---
name: external-apis
description: "Access external APIs through Replit-managed billing"
---

# External APIs

This skill provides access to external APIs through Replit-managed
passthrough billing. Requests are proxied through OpenInt with
managed credentials.

## Recommended workflow

1. Open the connector reference for request and response details.
2. Call `externalApi__<connector_name>` from `codeExecution`.
3. Use `query` for URL parameters and read `result.body`.
4. For media, save files under `attached_assets/` and present them.

## Response bodies

The callback decodes the response by Content-Type:

- JSON → `result.body` is the parsed object.
- `text/*` → `result.body` is a string.
- Anything else (binary, e.g. audio/image) → `result.body` is a base64 string and `result.encoding === 'base64'`. Decode it with `Buffer.from(result.body, 'base64')` before writing the file.

Responses are capped (~1 MB); larger media cannot be returned in-band yet. Prefer operations that return a hosted URL, or request smaller media until object-storage handoff is available.

## Available APIs

- [Brave](references/brave.md) - Search real web image results through Brave passthrough billing.
- [Browserbase](references/browserbase.md) - Web search and managed-browser page fetches through Browserbase passthrough billing.
- [ElevenLabs](references/elevenlabs.md) - Text-to-speech, music, and audio tools through ElevenLabs passthrough billing, subject to the ElevenLabs prohibited-use policy.
- [Exa](references/exa.md) - Semantic web search through Exa passthrough billing.
- [fal.ai](references/falai.md) - Bria RMBG background removal through fal.ai passthrough billing.
- [Firecrawl](references/firecrawl.md) - Scrape, crawl, and search the web through Firecrawl passthrough billing.
- [QuiverAI](references/quiver-ai.md) - Generate SVG icons and illustrations from a text prompt through QuiverAI passthrough billing.
- [Shotstack](references/shotstack.md) - Render videos, images, and audio from a JSON timeline through Shotstack passthrough billing.
- [Tripo3D](references/tripo3d.md) - Generate 3D models through Tripo3D passthrough billing.
- [X (Twitter)](references/x.md) - Read-only X API v2 access through passthrough billing.

