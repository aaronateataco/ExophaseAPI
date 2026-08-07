# ElevenLabs

Proxy requests to ElevenLabs via Replit-managed billing.

## Callback

Use `externalApi__elevenlabs` in `codeExecution`.

## Allowed operations

- `POST` `/v1/text-to-speech/:voice_id{/stream}?{/with-timestamps}?` - Text to Speech (non-streaming, streaming, with-timestamps, and stream/with-timestamps variants)
- `POST` `/v1/text-to-dialogue{/stream}?{/with-timestamps}?` - Text to Dialogue (multi-voice; non-streaming, streaming, with-timestamps, and stream/with-timestamps variants)
- `POST` `/v1/speech-to-text` - Speech to Text (Scribe v1/v2)
- `POST` `/v1/speech-to-speech/:voice_id{/stream}?` - Voice Changer (speech-to-speech; non-streaming and streaming variants)
- `POST` `/v1/sound-generation` - Sound Effects (text → sound generation)
- `POST` `/v1/audio-isolation{/stream}?` - Voice Isolator (audio-isolation; non-streaming and streaming variants)
- `POST` `/v1/forced-alignment` - Forced Alignment (audio + text → word/char timings)
- `POST` `/v1/text-to-voice/:variant(design|create-previews)` - Voice Design (text → three voice previews; charged once on response.text characters). Covers `/design` and legacy `/create-previews`.
- `POST` `/v1/text-to-voice/:voice_id/remix` - Voice Remix (remix existing voice → three previews; charged once on response.text characters). Shares billing mechanics with text_to_voice_design.
- `POST` `/v1/dubbing` - Dubbing v1 — creates a dub job; bills on response expected_duration_sec × tier-per-sec (watermark vs clean)
- `POST` `/v1/music{/:variant(detailed|stream)}?` - Music composition (non-streaming binary, multipart-detailed with JSON metadata, and event-stream variants)
- `POST` `/v1/music/video-to-music` - Video to Music (multipart videos → generated music matching combined video length)
- `POST` `/v1/music/stem-separation` - Music Stem Separation (split input audio into N stems; bills on multipart input file size ÷ nominal 128 kbps — see preamble for bitrate-assumption rationale)
- `GET` | `POST` | `PUT` | `PATCH` | `DELETE` `/:path+` - Catch-all — no charge for paths not explicitly listed (CRUD, metadata, workspace/convai management).

Authorization is handled automatically by Replit. Do not pass an `Authorization` header.

## Skill

## ElevenLabs quickstart

Text-to-speech, music, and audio tools through ElevenLabs
passthrough billing, subject to the ElevenLabs prohibited-use
policy. Replace path parameters like `:voice_id`
with real values — never send the pattern syntax literally. Send
required fields as an object in `body` (it is serialized for you
— do not pre-stringify).

```javascript
const voices = await externalApi__elevenlabs({
  path: '/v1/voices',
  method: 'GET',
})

const voiceId = voices.body.voices?.[0]?.voice_id
if (!voiceId) throw new Error('No ElevenLabs voices available')

const result = await externalApi__elevenlabs({
  path: '/v1/text-to-speech/' + voiceId + '/with-timestamps',
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: {text: 'Hello from Replit!', model_id: 'eleven_multilingual_v2'},
})

const audioBase64 = result.body.audio_base64

// File writes and imports are impure — keep them inside the
// "use impure" boundary; pass the (serializable) base64 string in.
await (async function (base64, out) {
  "use impure";
  const fs = await import('node:fs/promises')
  await fs.mkdir('attached_assets', {recursive: true})
  await fs.writeFile(out, Buffer.from(base64, 'base64'))
})(audioBase64, 'attached_assets/speech.mp3')
```

The `/with-timestamps` variant returns JSON with base64 audio,
which is easiest to save from a callback.

Authorization is managed by passthrough billing. Do not set an
`Authorization` header manually.

---

## Prohibited uses

Every ElevenLabs call is subject to the ElevenLabs Prohibited
Use Policy (https://elevenlabs.io/use-policy). If a request
falls under it, do not call `externalApi__elevenlabs` —
briefly explain why and continue with the parts of the task
that are allowed. Judge the real purpose of the requested
audio, not only the literal text to be spoken.

Never generate:

- Child sexual content, sexualization or grooming of minors,
  or content targeting minors with sexual, violent, or mature
  themes.
- Illegal activity: IP infringement, privacy violations, or
  facilitating illegal goods or services.
- Fraud or deception: phishing, scams, evading guardrails such
  as voice CAPTCHAs, unauthorized robocalls, or spam.
- Voice impersonation: replicating a real person's voice
  without consent or legal right, or using a replicated voice
  to harass or harm someone or to hide that it is
  AI-generated. Never clone a minor's voice.
- Elections: voter suppression, impersonating candidates or
  elected officials (even with authorization), or political
  campaigning, including soliciting votes or donations.
- Network attacks and surveillance: hacking, malware, spyware,
  or unauthorized monitoring of individuals.
- Non-fictional violence, hate, or harassment: threats,
  extremism, discrimination against protected groups,
  promoting self-harm, medical misinformation, or abusive debt
  collection. A villain's monologue in a game or audiobook is
  fine; so is news reporting on these topics.

Allowed only with conditions — flag or gate these:

- Professional financial, legal, or medical advice or
  services: requires qualified-professional review before
  output reaches consumers plus clear AI disclosure.
- Regulated goods (alcohol, tobacco, prescription meds,
  controlled substances, supplements, medical devices): use,
  acquisition, or exchange requires ElevenLabs' prior written
  authorization.
- Not permitted: real-money gambling, payday lending, or
  high-stakes automated decisions affecting individuals.
- AI voice agents must clearly disclose they are AI, not
  human.

The full policy summary, including platform rules (age limits,
government entities, machine-learning use of outputs), is in
`.local/skills/media-generation/elevenlabs-prohibited-uses.md`.
