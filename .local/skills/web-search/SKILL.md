---
name: web-search
description: Search the web, fetch content, extract branding profiles, and capture screenshots from URLs. Use for real-time information, API documentation, current events, design matching, and visual reference.
---

# Web Search Skill

## When to Use

- Real-time information (news, prices, events)
- Looking up API documentation or SDK guides
- Current technical information beyond training data
- Verifying facts from authoritative sources

## When NOT to Use

- Replit-specific features (use the `replit-docs` skill)
- Searching for real web images or logo files (use the `image-search` skill)
- Image or video generation (use the `media-generation` skill)
- Code search within the project (use grep/glob tools)

## Available Functions

### webSearch({ query, count?, category?, includeDomains?, isTextExtended? })

**Parameters:**

- `query` (str, required): Natural language search query phrased as a complete question
- `count` (number, optional): Number of results, 1-10
- `category` (str, optional): One of `company`, `people`, `news`, `personal site`. Response gains `publishedDate`, `author` and `entities`. `people` searches LinkedIn and each result's `entities[].properties` holds structured work history, education and location.
- `includeDomains` (list of str, optional): Limit to specific sites. Not allowed with `category: "people"`.
- `isTextExtended` (bool, optional): Increase returned text from 300 to 800 characters. Use when looking for high-pri info.

**Returns:** Dict with `searchAnswer` and `resultPages` (list of title/url/snippet dicts). Whenever you pass any argument beyond `query` and `count`, each result also carries `publishedDate`, `author` and `entities` where the search engine has them. `entities[].properties` is the structured record.

**Example:**

```javascript
const results = await webSearch({ query: "OpenAI API rate limits 2026" });
for (const page of results.resultPages) {
    console.log(`${page.title}: ${page.url}`);
}
```

### Multiple web searches

Issue one `webSearch({ query })` call per query and run the calls in parallel. The callback does not accept a `queries` array.

**Example:**

```javascript
const [openaiResults, anthropicResults] = await Promise.all([
    webSearch({ query: "OpenAI API rate limits 2026" }),
    webSearch({ query: "Anthropic API rate limits 2026" })
]);
```

### webFetch(url)

Fetch and extract content from a URL as markdown.

**Parameters:**

- `url` (str, required): Full HTTPS URL to fetch

**Returns:** Dict with `markdown` key containing page content

**Example:**

```javascript
const content = await webFetch({ url: "https://platform.openai.com/docs/guides/rate-limits" });
console.log(content.markdown.slice(0, 1000));
```

## Best Practices

1. **Use natural language queries**: write queries as complete questions with context.
2. **Chain search and fetch**: search first, then fetch specific pages for details.
3. **Be specific**: include dates, versions, or other specifics in queries.
4. **Verify with fetch**: don't rely only on search snippets for critical information.
5. **Use branding for design matching**: when replicating a site's visual style, use `extractBranding` to get exact colors, fonts, and spacing.
6. **Use screenshot for visual reference**: when you need to see what a site looks like before replicating its design.

## Example Workflow

```javascript
// Find information about a topic
const searchResult = await webSearch({ query: "FastAPI dependency injection tutorial 2026" });

// Get full content from the most relevant result
if (searchResult.resultPages.length > 0) {
    const bestUrl = searchResult.resultPages[0].url;
    const fullContent = await webFetch({ url: bestUrl });
    console.log(fullContent.markdown);
}
```

## Limitations

- You can search social media (LinkedIn, Instagram, Facebook, Reddit, YouTube), but you can't open the pages via `webFetch`. For people on LinkedIn use `category: "people"`.
- X/Twitter is not reached through either function. Read posts, users and trends with the separate `externalApi__x` function — see `.local/skills/external-apis/references/x.md`
- Cannot download media files (images, videos, audio)
- Paywalled or authenticated content may be inaccessible

## Copyright

- Respect copyright for media content from websites.
- You can reference or link to public content.
- Do not copy media files (images, videos, audio) directly from websites.
- Use the `media-generation` skill for images and videos instead.
