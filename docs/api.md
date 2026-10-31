# API

```bash
uv sync --locked --extra dev
uv run uvicorn music_store.api:app --host 127.0.0.1 --port 8000 --workers 1
```

Set `GEMINI_API_KEY` in `.env`. OpenAPI: `/docs` or `/openapi.json`.

| Endpoint | Purpose |
| --- | --- |
| `GET /health` | Local initialization status; makes no Gemini request. |
| `POST /chat` | Send a message; omit `session_id` to create a conversation. |
| `DELETE /sessions/{session_id}` | Delete conversation history. |

```bash
curl http://127.0.0.1:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"How much is the Yamaha C40 with PIX?"}'
```

The response contains `session_id`, `answer` and consulted tool names in `sources`.
Send the returned `session_id` with later messages to preserve context. Treat this
unguessable ID as private: there is no account authentication or order lookup.
Chat requests consume Gemini API quota.

Sessions stay in memory for 30 idle minutes, with a limit of 100. Use one worker;
restarts clear history. Concurrent messages/deletion for a busy session return
409; other sessions can proceed independently.

Invalid inputs return 422, unknown/expired sessions 404, configuration/authentication
errors 503, upstream quota errors 429 and other provider failures 502. Error details
include the session ID when a conversation was created, allowing a retry.

HTTP tests use simulated agent/provider responses. Manual Gemini smoke tests covered
catalog search and a PIX follow-up; submission recordings are still pending. See
[conversation examples](../examples/README.md). The command-line chat is also available.
