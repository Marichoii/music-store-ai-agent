# Gemini agent

The agent uses the official Google Gen AI SDK and `gemini-3.5-flash-lite`.
Five read-only tools handle categories, search, product lookup, quotes and policies.
Pydantic validates arguments before execution; the SDK never executes tools directly.

```bash
uv sync --locked --extra dev
cp .env.example .env
uv run python -m music_store --check-config
uv run python -m music_store
```

Set `GEMINI_API_KEY` locally before running. `GEMINI_MODEL` is configurable.
Configuration checks make no model requests. Chat sends messages and relevant
source context to Google and consumes API quota.

Each conversation owns its history. Complete Gemini contents and thought signatures
are retained for up to eight turns. Failed turns are discarded. Each turn permits
six tool rounds; requests have a 45-second timeout and at most two SDK attempts.

The first response must call a tool. Answers without a successful lookup are
blocked. This does not verify every sentence; real-model behavior still needs testing.
Offline tests use mock responses and the actual SDK over mocked HTTP transport.

References: [Google Gen AI SDK](https://googleapis.github.io/python-genai/#function-calling)
and [model documentation](https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite).
