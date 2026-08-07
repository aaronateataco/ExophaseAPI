---
name: development-environments
description: List the development environments available for creating sandboxes in the current Replit workspace.
---

# Development Environments

Development environments define the repositories included when creating a sandbox. Use this skill to discover the environments available in the current Replit workspace and inspect their repository configuration.

This skill only lists available environments. It cannot create a sandbox yet; sandbox creation will be added in a future skill.

## Available Functions

### listDevelopmentEnvironments()

List every development environment available for sandbox creation in the current Replit workspace.

**Returns:** `{ developmentEnvironments }` with each environment's `name` and `syncedRepositories`. Each synced repository includes its `url`, `ref`, and destination `path`.

```javascript
const { developmentEnvironments } = await listDevelopmentEnvironments({});
```
