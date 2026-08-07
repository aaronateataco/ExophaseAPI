# explainSchemaDiff()

Fetch the development→production database schema diff that publishing surfaces, so you can explain to the user *why* publishing wants to change the production schema and whether the change is destructive. It applies nothing to either database, but it is unavailable in Plan mode (resolving the production database provisions a read replica on first use). Call this when the user asks what the pending schema/database changes are before publishing, or when publishing warns about schema changes.

**Parameters:** none

**Returns:** Dict with:

- `success` (bool): `false` when the diff cannot be computed (e.g. database unavailable). On failure, `error` holds a message and no diff fields are present -- tell the user the diff is temporarily unavailable rather than asserting there are no changes.
- `hasDiff` (bool): `true` when production would change on publish. When `false`, the schemas already match.
- `statementsToExecute` (list[str]): the SQL statements publishing would run against production.
- `hasStructuralDataLoss` (bool): `true` when the change drops or truncates data-bearing structures. Warn the user prominently before they publish.
- `maybeNonBackwardsCompatible` (bool): `true` when the change may break the currently-running production app during rollout.
- `warnings` (list[str]): human-readable notes about the diff.
- `tablesToRemove` / `tablesToTruncate` / `columnsToRemove` / `schemasToRemove` / `matViewsToRemove` (list[str]): names of objects the diff would drop or truncate. Any non-empty list here is destructive -- surface it explicitly.

**These results are a worst case, not the definitive publish plan.** The diff resolves schema conflicts non-interactively with safe defaults (create/drop, never rename), whereas the interactive publish flow lets the user resolve a *rename*. So a column/table shown as dropped-and-recreated (data loss) may actually be a renamed one that publishing can migrate without losing data. When you report destructive changes, tell the user they are the worst case and that the publish dialog may offer a rename that preserves the data -- do not assert the data will definitely be lost.

**Example:**

```javascript
const diff = await explainSchemaDiff();
if (!diff.success) {
    console.log("Schema diff unavailable right now; try again shortly.");
} else if (!diff.hasDiff) {
    console.log("Production schema already matches -- nothing to migrate.");
} else {
    console.log(`${diff.statementsToExecute.length} statement(s) will run on publish.`);
    if (diff.hasStructuralDataLoss || diff.tablesToRemove.length || diff.columnsToRemove.length) {
        console.log("WARNING: destructive change.", {
            tablesToRemove: diff.tablesToRemove,
            columnsToRemove: diff.columnsToRemove,
        });
    }
}
```
