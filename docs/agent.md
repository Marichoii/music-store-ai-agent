# Gemini agent

The agent uses the official Google Gen AI SDK and `gemini-3.5-flash-lite`.
Five read-only tools handle categories, search, product lookup, quotes and policies.
Pydantic validates arguments before execution; the SDK never executes tools directly.
Search results contain prices, availability and source warnings. Full descriptions
and specifications are retrieved with `get_product` when needed.

Customer replies follow the latest message's language, including mid-conversation
switches. Language-neutral follow-ups keep the last established customer language.
Product names and source identifiers stay unchanged.
`langdetect` selects a language locally when confidence is high; short neutral
messages retain the session language. Each model request names that language,
and confidently detected mismatches are rejected. After each tool lookup, a
reminder repeats the current customer message. Short or mixed-language text can
still be ambiguous.
Short messages are disambiguated between Portuguese and English. Product
names retain the session language; agent failure messages support Portuguese and English.

Set `GEMINI_API_KEY` and optionally `GEMINI_MODEL` in `.env`.
The HTTP interface is documented in [api.md](api.md). Chat sends messages and
relevant source context to Google and consumes API quota.

Each conversation owns its history. Complete Gemini contents and thought signatures
are retained for up to eight turns. Failed turns are discarded. Each turn permits
six tool rounds; requests have a 45-second timeout and at most two SDK attempts.

The first response must call a tool. Answers without a successful lookup are
blocked. This does not verify every sentence; [recorded conversations](../examples/README.md)
document the live-model checks.
Offline tests use mock responses and the actual SDK over mocked HTTP transport.

References: [Google Gen AI SDK](https://googleapis.github.io/python-genai/#function-calling)
and [model documentation](https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite).
