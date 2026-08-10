"""CLI argument handling and exit codes.

The CLI is the contract most users touch first, so exit codes and the offline
``--check`` path are pinned here.
"""

from __future__ import annotations

import pytest

from main import apply_overrides, build_parser, main
from forex.config import Config
from forex.providers import ProviderManager

from tests.helpers import StubProvider

CLI_ENV_VARS = (
    "FOREX_SYMBOLS", "FOREX_TIMEFRAMES", "FOREX_BARS", "FOREX_PROVIDER",
    "FOREX_OUTPUT_DIR", "FOREX_REPORT_FORMAT", "LLM_API_KEY", "OPENAI_API_KEY",
    "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID",
)


@pytest.fixture(autouse=True)
def isolate_env(monkeypatch, tmp_path):
    for name in CLI_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("FOREX_OUTPUT_DIR", str(tmp_path / "out"))
    monkeypatch.chdir(tmp_path)


@pytest.fixture
def stub_pipeline(monkeypatch):
    """Force the pipeline to use an offline stub provider."""
    monkeypatch.setattr(
        "forex.pipeline.ProviderManager", lambda *a, **k: ProviderManager([StubProvider("stub")])
    )


class TestArgumentParsing:
    def test_defaults_are_empty(self):
        args = build_parser().parse_args([])
        assert args.symbols is None
        assert args.dry_run is False
        assert args.check is False

    def test_symbols_override_config(self):
        args = build_parser().parse_args(["--symbols", "EURUSD,GBPUSD"])
        config = apply_overrides(Config.from_env(dotenv_path=None), args)
        assert config.symbols == ["EURUSD", "GBPUSD"]

    def test_timeframes_uppercased(self):
        args = build_parser().parse_args(["--timeframes", "h1,d1"])
        assert apply_overrides(Config.from_env(dotenv_path=None), args).timeframes == ["H1", "D1"]

    def test_format_choice_enforced(self):
        with pytest.raises(SystemExit):
            build_parser().parse_args(["--format", "pdf"])

    def test_bars_and_provider_override(self):
        args = build_parser().parse_args(["--bars", "50", "--provider", "yfinance"])
        config = apply_overrides(Config.from_env(dotenv_path=None), args)
        assert config.bars == 50
        assert config.preferred_provider == "yfinance"


class TestCheckMode:
    def test_check_exits_zero_offline(self, capsys):
        """--check must never need the network."""
        assert main(["--check"]) == 0
        out = capsys.readouterr().out
        assert "Configuration" in out
        assert "Data providers" in out

    def test_check_lists_resolved_symbols(self, capsys):
        main(["--check", "--symbols", "EURUSD,USDJPY"])
        assert "EUR/USD, USD/JPY" in capsys.readouterr().out

    def test_check_reports_llm_off_without_key(self, capsys):
        main(["--check"])
        assert "LLM commentary: off" in capsys.readouterr().out


class TestInvalidInput:
    def test_bad_symbol_exits_two(self, capsys):
        assert main(["--symbols", "NOTAPAIR"]) == 2
        assert "Symbol error" in capsys.readouterr().err

    def test_bad_symbol_in_check_mode_exits_two(self):
        assert main(["--check", "--symbols", "EURUSD,ZZZZZZ"]) == 2


class TestRunExitCodes:
    def test_successful_run_exits_zero(self, stub_pipeline, capsys):
        code = main(["--symbols", "EURUSD", "--dry-run"])
        assert code == 0
        assert "Daily Forex Analysis" in capsys.readouterr().out

    def test_total_failure_exits_one(self, monkeypatch, capsys):
        monkeypatch.setattr(
            "forex.pipeline.ProviderManager",
            lambda *a, **k: ProviderManager([StubProvider("broken", fail_on=["*"])]),
        )
        assert main(["--symbols", "EURUSD", "--dry-run"]) == 1

    def test_partial_failure_still_exits_zero(self, monkeypatch):
        """One good pair is a usable result."""
        class Selective(StubProvider):
            def fetch(self, instrument, timeframe, bars):
                if instrument.symbol == "USDJPY":
                    raise RuntimeError("down")
                return super().fetch(instrument, timeframe, bars)

        monkeypatch.setattr(
            "forex.pipeline.ProviderManager", lambda *a, **k: ProviderManager([Selective("sel")])
        )
        assert main(["--symbols", "EURUSD,USDJPY", "--dry-run"]) == 0

    def test_json_output_parses(self, stub_pipeline, capsys):
        import json

        main(["--symbols", "EURUSD", "--dry-run", "--format", "json"])
        assert json.loads(capsys.readouterr().out)["summary"]["succeeded"] == 1

    def test_report_written_and_path_reported(self, stub_pipeline, capsys, tmp_path):
        import os

        assert main(["--symbols", "EURUSD", "--no-push"]) == 0
        err = capsys.readouterr().err
        assert "Report written to" in err
        path = err.split("Report written to ")[1].splitlines()[0].strip()
        assert os.path.isfile(path)
