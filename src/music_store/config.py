"""Load local Gemini configuration."""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]


class ConfigurationError(ValueError):
    """Invalid or missing configuration."""


@dataclass(frozen=True)
class Settings:
    api_key: str = field(repr=False)
    model: str = "gemini-3.5-flash-lite"
    timeout_seconds: int = 45
    max_tool_rounds: int = 6
    max_history_turns: int = 8

    def __post_init__(self):
        if not self.model.strip():
            raise ConfigurationError("GEMINI_MODEL must not be empty.")
        if not 5 <= self.timeout_seconds <= 120:
            raise ConfigurationError("Timeout must be between 5 and 120 seconds.")
        if not 1 <= self.max_tool_rounds <= 10 or not 1 <= self.max_history_turns <= 20:
            raise ConfigurationError("Invalid tool-round or history limit.")

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv(ROOT / ".env", override=False)
        return cls(
            api_key=os.getenv("GEMINI_API_KEY", "").strip(),
            model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite").strip(),
        )

    def require_api_key(self) -> None:
        if not self.api_key or self.api_key.upper() in {"REDACTED", "YOUR_API_KEY"}:
            raise ConfigurationError("Set GEMINI_API_KEY in your local .env file to use the agent.")
