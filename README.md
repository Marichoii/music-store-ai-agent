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

## Run

Set `GEMINI_API_KEY` in a local `.env`, using `.env.example` as a template.

```bash
uv sync --locked --extra dev
uv run uvicorn music_store.api:app --host 127.0.0.1 --port 8000 --workers 1
```

Open [API docs](http://127.0.0.1:8000/docs). Details: [API usage](docs/api.md).

Record real [conversation examples](examples/README.md) through the running API.

## AI assistance

OpenAI Codex supports planning, coding, tests and documentation.
