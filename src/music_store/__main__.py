"""Run the agent in a terminal."""

import argparse

from music_store.agent import Conversation, StoreAgent, create_client
from music_store.catalog import Catalog, CatalogError
from music_store.config import ConfigurationError, Settings
from music_store.policies import PolicyBook, PolicyError
from music_store.tools import StoreTools


def main() -> int:
    parser = argparse.ArgumentParser(description="Empório da Música assistant")
    parser.add_argument("--check-config", action="store_true")
    args = parser.parse_args()
    try:
        settings = Settings.from_env()
        settings.require_api_key()
        tools = StoreTools(Catalog.load(), PolicyBook())
    except (ConfigurationError, CatalogError, PolicyError) as exc:
        print(str(exc))
        return 1
    if args.check_config:
        print("Configuration and sources are ready. No model request sent.")
        return 0
    try:
        with create_client(settings) as client:
            agent = StoreAgent(client, settings, tools)
            conversation = Conversation()
            print("Empório da Música — type 'exit' to quit.")
            while True:
                try:
                    message = input("You: ").strip()
                except (EOFError, KeyboardInterrupt):
                    print()
                    break
                if message.casefold() in {"exit", "quit"}:
                    break
                if message:
                    print("Assistant:", agent.reply(message, conversation).answer)
    except Exception:
        print("The Gemini client could not be initialized.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
