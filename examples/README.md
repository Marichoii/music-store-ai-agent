# Conversation examples

## Recorded conversations

Captured on November 1, 2026 (UTC), through the running FastAPI application using
`gemini-3.5-flash-lite`. Customer messages are scripted; assistant answers are
unedited model output. Each Markdown file has a matching JSON record.

| Conversation | Coverage |
| --- | --- |
| [Budget](run-20261101T004615419751Z/budget.md) | Available nylon-string guitars under BRL 700; PIX follow-up. |
| [Promotions](run-20261101T004615419751Z/promotions.md) | Active 18% promotion and non-cumulative PIX discount. |
| [Returns](run-20261101T004615419751Z/returns.md) | Online regret, product condition and unsupported refund actions. |
| [Limits](run-20261101T004615419751Z/limits.md) | Out-of-scope request and undefined freight at exactly BRL 500. |

Reviewed against the supplied CSVs and manual: the Tagima PIX quote is BRL 408.41;
the Crafter promotion remains BRL 1,967.18 with PIX. A return is not processed or
guaranteed, and freight at exactly BRL 500 requires store confirmation.

Preliminary runs exposed a provider quota limit, language drift and an unsupported
freight inference. The final recordings follow the language and freight fixes.

## Record another run

With the API running, record four English conversations (eight messages):

```bash
uv run python -m music_store.record_examples
```

This makes real Gemini requests through `POST /chat` and consumes API quota.
Use `--scenario budget` to record only one conversation. Other scenarios:
`promotions`, `returns` and `limits`.
If the provider returns HTTP 429, wait for quota to become available and retry
the affected scenario. The included run spaced scenario groups to avoid this limit.

Each run creates a new dated directory with Markdown conversations and matching
JSON records. Assistant text and consulted tool names are preserved; session IDs
are omitted and sessions are deleted after recording. Failures stop the run and
leave an `incomplete` recording.

Review the answers against the original sources. `complete` means every HTTP
request succeeded, not that the answers were independently verified. Include
three to five complete conversations in the submission.
