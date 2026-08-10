"""Configuration loaded from environment variables and an optional .env file.

Nothing is hardcoded and nothing is required: the tool runs with zero
configuration using a keyless data provider, and every capability that needs a
credential degrades to "off" rather than crashing. That is what makes the repo
usable by anyone with their own keys.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List, Optional


def _env(name: str, default: str = "") -> str:
    value = os.getenv(name)
    return default if value is None else value.strip()


def _env_int(name: str, default: int) -> int:
    raw = _env(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    raw = _env(name)
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_bool(name: str, default: bool = False) -> bool:
    raw = _env(name).lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes", "on")


def load_dotenv(path: str = ".env") -> None:
    """Load ``KEY=value`` pairs from a .env file without overriding real env vars.

    Uses python-dotenv when installed and falls back to a minimal parser so the
    package has no hard dependency on it.
    """
    try:
        from dotenv import load_dotenv as _load

        _load(path, override=False)
        return
    except ImportError:
        pass

    if not os.path.exists(path):
        return

    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


@dataclass
class LLMConfig:
    """Any OpenAI-compatible chat completions endpoint.

    Defaults target OpenAI, but ``LLM_BASE_URL`` lets users point at OpenRouter,
    DeepSeek, Groq, Together, or a local llama.cpp/vLLM server unchanged.
    """

    api_key: str = ""
    model: str = "gpt-4o-mini"
    base_url: str = "https://api.openai.com/v1"
    temperature: float = 0.3
    max_tokens: int = 1600
    timeout: int = 90

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    @classmethod
    def from_env(cls) -> "LLMConfig":
        # Accept common vendor-specific key names so users need not rename theirs.
        api_key = (
            _env("LLM_API_KEY")
            or _env("OPENAI_API_KEY")
            or _env("OPENROUTER_API_KEY")
            or _env("DEEPSEEK_API_KEY")
            or _env("GROQ_API_KEY")
        )
        return cls(
            api_key=api_key,
            model=_env("LLM_MODEL", "gpt-4o-mini"),
            base_url=_env("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
            temperature=_env_float("LLM_TEMPERATURE", 0.3),
            max_tokens=_env_int("LLM_MAX_TOKENS", 1600),
            timeout=_env_int("LLM_TIMEOUT", 90),
        )


@dataclass
class TelegramConfig:
    bot_token: str = ""
    chat_id: str = ""

    @property
    def enabled(self) -> bool:
        return bool(self.bot_token and self.chat_id)

    @classmethod
    def from_env(cls) -> "TelegramConfig":
        return cls(
            bot_token=_env("TELEGRAM_BOT_TOKEN"),
            chat_id=_env("TELEGRAM_CHAT_ID"),
        )


@dataclass
class Config:
    """Top-level runtime configuration."""

    symbols: List[str] = field(default_factory=list)
    timeframes: List[str] = field(default_factory=lambda: ["H1", "H4", "D1"])
    bars: int = 300
    preferred_provider: str = ""
    output_dir: str = "reports"
    report_format: str = "markdown"
    log_level: str = "INFO"
    llm: LLMConfig = field(default_factory=LLMConfig)
    telegram: TelegramConfig = field(default_factory=TelegramConfig)

    @classmethod
    def from_env(cls, dotenv_path: Optional[str] = ".env") -> "Config":
        if dotenv_path:
            load_dotenv(dotenv_path)

        raw_symbols = _env("FOREX_SYMBOLS")
        symbols = [s.strip() for s in raw_symbols.split(",") if s.strip()] if raw_symbols else []

        raw_timeframes = _env("FOREX_TIMEFRAMES")
        timeframes = (
            [t.strip().upper() for t in raw_timeframes.split(",") if t.strip()]
            if raw_timeframes
            else ["H1", "H4", "D1"]
        )

        return cls(
            symbols=symbols,
            timeframes=timeframes,
            bars=_env_int("FOREX_BARS", 300),
            preferred_provider=_env("FOREX_PROVIDER"),
            output_dir=_env("FOREX_OUTPUT_DIR", "reports"),
            report_format=_env("FOREX_REPORT_FORMAT", "markdown").lower(),
            log_level=_env("LOG_LEVEL", "INFO").upper(),
            llm=LLMConfig.from_env(),
            telegram=TelegramConfig.from_env(),
        )

    def describe(self) -> str:
        """Human-readable summary of which optional features are active."""
        lines = [
            f"symbols: {', '.join(self.symbols) if self.symbols else '(default watchlist)'}",
            f"timeframes: {', '.join(self.timeframes)}",
            f"provider preference: {self.preferred_provider or '(automatic fallback)'}",
            f"LLM commentary: {'on (' + self.llm.model + ')' if self.llm.enabled else 'off (no API key)'}",
            f"Telegram push: {'on' if self.telegram.enabled else 'off (no bot token/chat id)'}",
            f"output: {self.output_dir} ({self.report_format})",
        ]
        return "\n".join(lines)
