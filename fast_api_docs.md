    # ADK Fast API Documentation

A REST + WebSocket interface for managing **Agent Development Kit (ADK)** apps, sessions, artifacts, evaluations, and live runs.

> **Base URL**: `http://<host>:<port>` (default `http://localhost:8000`)

---

## Conventions

| Symbol | Meaning |
|--------|---------|
| `{param}` | Path parameter (required) |
| `?param=` | Query parameter (optional) |
| `⟳` | Streaming / long‑lived endpoint |
| `💬` | WebSocket endpoint |

All responses are JSON unless otherwise noted. Standard error shape:

```json
{
  "detail": "Human‑readable error message"
}
```

---

## 1. Meta

### List available agent apps  
`GET  /list-apps`

| Success | 200 OK → `string[]` |
|---------|---------------------|
| Failure | 404 Path not found&nbsp;• 400 Not a directory |

---

### Fetch an OpenTelemetry trace  
`GET  /debug/trace/{event_id}`

| Path param | Type | Description |
|------------|------|-------------|
| `event_id` | `string` | The event ID captured from an `Event` |

| Success | 200 OK → `object` (trace dict) |
|---------|--------------------------------|
| Failure | 404 Trace not found |

---

## 2. Sessions

### Get a single session  
`GET  /apps/{app_name}/users/{user_id}/sessions/{session_id}`

| Path param | Type | Description |
|------------|------|-------------|
| `app_name` | `string` | Root Python package of the agent app |
| `user_id`  | `string` | User identifier |
| `session_id` | `string` | Session identifier |

| Success | 200 OK → `Session` |
|---------|--------------------|
| Failure | 404 Session not found |

---

### List a user’s sessions  
`GET  /apps/{app_name}/users/{user_id}/sessions`

Returns `Session[]` **excluding** auto‑generated evaluation sessions (`EVAL_*`).

---

### Create a session (client‑supplied ID)  
`POST /apps/{app_name}/users/{user_id}/sessions/{session_id}`

| Body field | Type | Description |
|------------|------|-------------|
| `state`    | `object` optional | Initial session state |

| Success | 201 Created → `Session` |
|---------|-------------------------|
| Failure | 400 Session already exists |

---

### Create a session (server‑generated ID)  
`POST /apps/{app_name}/users/{user_id}/sessions`

Same body as above. Responds with newly generated `session_id`.

---

### Delete a session  
`DELETE /apps/{app_name}/users/{user_id}/sessions/{session_id}` → **204 No Content**

---

## 3. Evaluation Sets

| Action | Verb & Path |
|--------|-------------|
| **Create eval set** | `POST /apps/{app_name}/eval_sets/{eval_set_id}` |
| **List eval sets** | `GET  /apps/{app_name}/eval_sets` |
| **Add session → eval set** | `POST /apps/{app_name}/eval_sets/{eval_set_id}/add_session` |
| **List evals in set** | `GET  /apps/{app_name}/eval_sets/{eval_set_id}/evals` |
| **Run eval(s)** | `POST /apps/{app_name}/eval_sets/{eval_set_id}/run_eval` |

### Create eval set

`eval_set_id` must match `^[a‑zA‑Z0‑9_]+$`. A new file `{eval_set_id}.evalset.json` is created in the app directory.

### Add session → eval set

Body schema:

```jsonc
{
  "eval_id":   "string",   // unique within the set
  "session_id":"string",
  "user_id":   "string"
}
```

Errors:

- 400 Invalid ID format
- 400 Eval ID already exists
- 404 Session not found

### Run eval(s)

Body schema:

```jsonc
{
  "eval_ids":     ["eval1", "eval2"], // empty array → run all
  "eval_metrics": ["accuracy", "bleu"]
}
```

Returns `RunEvalResult[]`.

---

## 4. Artifacts (session files)

| Endpoint | Description |
|----------|-------------|
| `GET  /apps/{app}/users/{user}/sessions/{sess}/artifacts` | List artifact names |
| `GET  /apps/{app}/users/{user}/sessions/{sess}/artifacts/{name}?version=` | Get latest / specific version |
| `GET  /apps/{app}/users/{user}/sessions/{sess}/artifacts/{name}/versions` | List version numbers |
| `GET  /apps/{app}/users/{user}/sessions/{sess}/artifacts/{name}/versions/{version_id}` | Get exact version |
| `DELETE /apps/{app}/users/{user}/sessions/{sess}/artifacts/{name}` | Delete all versions |

Common errors: 404 Artifact not found.

---

## 5. Running Agents

### One‑shot run  
`POST /run`

Body schema (**AgentRunRequest**):

```jsonc
{
  "app_name":   "sales_assistant",
  "user_id":    "u123",
  "session_id": "s456",
  "new_message":"Hello!",
  "streaming":  false
}
```

Returns full list of `Event` objects executed.

---

### Server‑Sent Events run ⟳  
`POST /run_sse`

- Same payload as `/run`
- If `streaming = true`, each `Event` is emitted as `data: {...}\n\n`
- `Content‑Type: text/event-stream`

---

### Live bidirectional run 💬  
`WS  /run_live?app_name=…&user_id=…&session_id=…&modalities=TEXT,AUDIO`

**Client → Server**: `LiveRequest` JSON  
**Server → Client**: `Event` JSON stream

Query param `modalities` may include `TEXT` and/or `AUDIO`.

---

## 6. Event Graph

`GET /apps/{app}/users/{user}/sessions/{sess}/events/{event_id}/graph`

Returns:

```json
{ "dot_src": "digraph {...}" }
```

Empty object if no function calls detected.

---

## 7. Embedded Dev UI _(optional)_

Enabled when server started with `web=True`.

| Path | Purpose |
|------|---------|
| `/` → 302 `/dev-ui` | Redirect |
| `/dev-ui` | Angular SPA entry point |
| `/*`      | Static assets |

---

### Status Codes Reference

| Code | Meaning |
|------|---------|
| 200 OK | Successful GET |
| 201 Created | Successful POST (creation) |
| 204 No Content | Successful DELETE |
| 400 Bad Request | Validation / duplicate errors |
| 404 Not Found | Resource missing |
| 422 Unprocessable Entity | Pydantic validation errors (autogenerated) |
| 500 Internal Server Error | Unhandled server exception |

---

## Change Log

- **v1.0** – Initial public documentation (2025‑05‑03)
