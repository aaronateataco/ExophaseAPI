---
name: llm-query
description: Ask an internal LLM a focused question about large text or structured content using the queryWithLLM CodeExecution callback. Use when content is too large or noisy to inspect manually and you need a concise answer with line citations, or a structured answer available in CodeExecution.
---

# LLM Query Skill

## When to Use

- You already have large text or structured JSON inside CodeExecution and need a focused answer.
- You need line citations into the provided content.
- You want to avoid logging or printing a large payload into CodeExecution output.

## When NOT to Use

- Full-content transformation: translating, reformatting, or rewriting large content. The answer is capped at 200000 bytes, so transformation output proportional to a large input fails. Split the content into chunks and transform each chunk with a separate call, keeping each expected answer well under the cap.

## Available Functions

### `queryWithLLM({ content, query, truncationStrategy?, responseSchema? })`

Ask an internal LLM a narrow question about provided content.

**Parameters:**

- `content` (string | JSON value, required): content to ask about. String content is used as-is; structured JSON is formatted.
- `query` (string, required): non-empty question or instruction about the content.
- `truncationStrategy` (`"head_tail"` | `"head_only"` | `"none"`, optional): defaults to `"head_tail"`. Use `"none"` when the complete content must fit and failing is better than truncating.
- `responseSchema` (JSON Schema, optional): returns a validated structured JSON response instead of text. Prefer simple schemas with required fields.

**Returns:** string answer capped at 200000 bytes, or a JSON value matching `responseSchema`. Text answers should cite relevant content line numbers.

**Example:**

```javascript
const answer = await queryWithLLM({
  content: largeLogText,
  query: 'What is the first error and likely root cause?',
});
console.log(answer);
```

For structured responses, provide a simple JSON schema with required fields. Prefer objects, arrays, primitive values, and enums; avoid complex schema features unless necessary.

```javascript
const result = await queryWithLLM({
  content: deploymentLog,
  query: 'Extract the deployment status and version.',
  responseSchema: {
    type: 'object',
    properties: {
      status: { type: 'string', enum: ['success', 'failure', 'unknown'] },
      version: { type: 'string' },
    },
    required: ['status', 'version'],
    additionalProperties: false,
  },
});
```

**Structured example:**

```javascript
const answer = await queryWithLLM({
  content: { files: changedFiles, diagnostics },
  query: 'Which diagnostic should be fixed first?',
  truncationStrategy: 'head_tail',
});
console.log(answer);
```

## Best Practices

1. Ask a narrow question; do not use this callback as a general chat model.
2. Do not echo the full input or full answer unless the user needs it; summarize the relevant result.
3. Use `truncationStrategy: "none"` when truncation could hide critical data, and handle the size error.
4. The callback redacts tracing for safety, but the answer is still returned to your script. Treat source code, tokens, keys, and secrets carefully.
