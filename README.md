# Empório da Música — customer-service assistant

Python prototype for the Artefact AI Engineer technical challenge.

## Current stage

The Python package and development environment are configured. Catalog queries,
pricing rules, policy consultation, Gemini integration and the chat interface will
be added in separate steps. No assistant or real model calls are implemented yet.

This branch reconstructs the project from its initial commit. The previously
completed prototype remains preserved on `prototype-backup`.

## Development setup

Use Python 3.12 and uv. From this branch's working directory:

```bash
uv sync --locked --extra dev
uv run python -c "import music_store; print('Package import OK')"
uv run ruff check .
uv run ruff format --check .
```

`pyproject.toml` defines the package and development tools. `uv.lock` records the
resolved dependency versions. Runtime dependencies will be added when needed.

Local `.env` files and virtual environments are excluded from Git. Keep real API
keys in `.env`; never add them to example files or commits.

## AI assistance

OpenAI Codex assists with implementation, automated verification and documentation.
Candidate review and real Gemini validation will be recorded only after they occur.
