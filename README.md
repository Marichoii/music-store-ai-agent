# Empório da Música — customer-service assistant

Project for Artefact's **AI Engineer — Full-Stack for Generative AI Applications**
technical challenge.

## The challenge

Empório da Música is a fictional instrument store in Campo Grande/MS, Brazil.
The goal is to build a Python assistant that answers customer questions using
the supplied CSV files and policy manual.

## Expected behavior

- Find instruments by category, budget and availability.
- Check prices, stock and active promotions.
- Explain hours, payments, delivery, exchanges and returns.
- Handle follow-ups, missing information and out-of-scope requests.
- Use a welcoming, informal and professional tone.

## Stack

**Python**, **Gemini** and **FastAPI**, with Python tools for data queries and
business rules.

## Technical decisions

- **Gemini:** structured function calling and Portuguese/English responses through
  the official SDK. The default is `gemini-3.5-flash-lite`; override it with
  `GEMINI_MODEL`.
- **FastAPI:** validated requests and interactive OpenAPI documentation provide
  a small, testable interface without a separate frontend.
- **Python tools:** one agent delegates read-only catalog queries, stock checks
  and monetary calculations to validated functions. `Decimal` handles rounding
  and discount rules; the model handles conversation.
- **Full PDF context:** the manual has eight pages. Returning all pages with
  references and ambiguity notes keeps exceptions together without a vector
  database or a retrieval step that might miss a relevant rule.
- **Language matching:** `langdetect` supplies an explicit reply language locally
  without an extra model call; neutral follow-ups retain the session language.

The prompt defines tone, language matching, source lookup and uncertainty handling.
Messages and source text are treated as data; tools have an explicit allowlist.
Conversation history is isolated by session and limited to eight turns.

## Run

Requires Python 3.12 and `uv`.

Set `GEMINI_API_KEY` in a local `.env`, using `.env.example` as a template.

```bash
uv sync --locked --extra dev
uv run uvicorn music_store.api:app --host 127.0.0.1 --port 8000 --workers 1
```

Open [API docs](http://127.0.0.1:8000/docs). Details: [API usage](docs/api.md).

Record real [conversation examples](examples/README.md) through the running API.

## Checks

```bash
uv run pytest -q
uv run ruff check .
```

Technical details: [agent](docs/agent.md), [data](data/README.md) and
[policy assumptions](docs/policies.md).

## Limitations

- CSVs are snapshots, not live inventory. No order lookup, checkout, refunds or
  reservations are implemented.
- Sessions stay in memory for 30 idle minutes. Use one worker; restarting clears
  history. There is no account authentication; this is a local prototype.
- Conflicting policies require store confirmation. A successful tool call does
  not guarantee every sentence is correct; model responses still need review.
- Short-message detection is tuned for Portuguese and English. Other languages
  and mixed-language messages receive best-effort handling.

With more time, I would expand live-model evaluations and add authenticated,
shared session storage for deployment. A larger manual would justify retrieval
of specific sections.

## AI assistance

OpenAI Codex assisted with planning, source-data analysis, coding, tests and
documentation. Automated tests check the implementation; recorded API runs
provide real-model examples.
