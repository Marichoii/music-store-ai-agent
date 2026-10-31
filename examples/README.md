# Conversation examples

With the API running, record four English conversations (eight messages):

```bash
uv run python -m music_store.record_examples
```

This makes real Gemini requests through `POST /chat` and consumes API quota.
Use `--scenario budget` to record only one conversation. Other scenarios:
`promotions`, `returns` and `limits`.

Each run creates a new dated directory. JSON files preserve the assistant's text
and consulted tool names; session IDs are omitted and sessions are deleted after
recording. Failures stop the run and leave an `incomplete` recording.

Review the answers against the original sources. `complete` means every HTTP
request succeeded, not that the answers were independently verified. Include
three to five complete conversations in the submission. No generated examples
have been committed yet; the recorder's offline tests use simulated responses.
