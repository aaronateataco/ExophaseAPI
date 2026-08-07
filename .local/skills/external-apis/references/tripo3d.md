# Tripo3D

Proxy requests to Tripo3D via Replit-managed billing.

## Callback

Use `externalApi__tripo3d` in `codeExecution`.

## Allowed operations

- `POST` `/task` - Submit a Tripo3D generation task. Cost is read from data.consumed_credit on GET /v2/openapi/task/{task_id} after the task reaches a terminal status. Covers every billable body.type uniformly.
- `GET` `/task/:task_id` - Poll a previously submitted task by id. Free — Tripo does not charge for status queries.

Authorization is handled automatically by Replit. Do not pass an `Authorization` header.

## Skill

## Tripo3D quickstart

Generate 3D models through Tripo3D passthrough billing. Submit a
generation task, poll it, then download the model. Send the
required fields as an object in `body` (it is serialized for you
— do not pre-stringify).

```javascript
const submit = await externalApi__tripo3d({
  path: '/task',
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: {type: 'text_to_model', prompt: 'a low-poly wooden chair'},
})

const taskId = submit.body.data.task_id
let modelUrl
for (let attempt = 0; attempt < 60; attempt++) {
  await new Promise((resolve) => setTimeout(resolve, 5000))
  const task = await externalApi__tripo3d({
    path: '/task/' + taskId,
    method: 'GET',
  })
  if (task.body.data.status === 'success') {
    modelUrl = task.body.data.output.pbr_model ?? task.body.data.output.model
    break
  }
  if (['failed', 'banned', 'expired', 'cancelled', 'unknown'].includes(task.body.data.status)) {
    throw new Error('Tripo3D task did not succeed')
  }
}

if (!modelUrl) throw new Error('Tripo3D task did not finish in time')

console.log(modelUrl)
```

Model download URLs expire a few minutes after the task completes
— fetch them promptly. Authorization is managed by passthrough
billing. Do not set an `Authorization` header manually.

## Example

```javascript
const result = await externalApi__tripo3d({
  path: '/task',
  method: 'POST',
  body: {},
})

console.log(result.status)
console.log(result.body)
```
