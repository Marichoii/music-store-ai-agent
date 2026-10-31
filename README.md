# Empório da Música — customer-service assistant

Project for Artefact's **AI Engineer — Full-Stack for Generative AI Applications**
technical challenge.

## The challenge

Empório da Música is a fictional musical instrument store in Campo Grande, Brazil.
Its team handles recurring customer questions about products, prices, availability
and store policies.

The challenge is to build a Python customer-service agent that answers text
messages using the supplied operational CSV files and store policy manual.

## Expected behavior

- Use a welcoming, informal and professional tone.
- Help customers find instruments by category, budget and availability.
- Consult product data before providing prices, stock or active promotions.
- Explain opening hours, payment methods, delivery, exchanges and returns using
  the store's policies.
- Maintain context for follow-up questions.
- Recognize requests outside the store's scope and acknowledge missing or
  ambiguous information.

## Planned approach

The application will use **Python**, **Gemini** for language understanding and tool
calling, and **Streamlit** for a simple chat interface. Python functions will query
the supplied data and apply pricing rules. The policy manual will provide the
reference for answers about store procedures.

## AI assistance

OpenAI Codex is used to support planning, implementation, automated checks and
documentation.
