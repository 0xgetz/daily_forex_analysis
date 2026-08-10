"""Report rendering: Markdown for humans, JSON for machines."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_DISCLAIMER = (
    "Technical analysis generated from public market data for educational "
    "purposes. Not investment advice. Verify prices with your broker before "
    "acting on anything here."
)

_ARROWS = {"up": "▲", "down": "▼", "sideways": "→", "conflicted": "⚠", "unknown": "?"}


def _fmt(value: Optional[float], digits: int = 1, suffix: str = "") -> str:
    if value is None:
        return "n/a"
    return f"{value:.{digits}f}{suffix}"


def render_json(payload: Dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, default=str)


def _render_pair_section(pair: Dict[str, Any]) -> List[str]:
    lines: List[str] = []
    alignment = pair.get("alignment", {})
    verdict = alignment.get("verdict", "unknown")

    lines.append(f"### {pair['pretty']}  {_ARROWS.get(verdict, '')}")
    lines.append("")

    if pair.get("error"):
        lines.append(f"Data unavailable: {pair['error']}")
        lines.append("")
        return lines

    lines.append(
        f"Last price {pair.get('last_price_display', 'n/a')} "
        f"(source: {pair.get('source', 'unknown')})"
    )
    lines.append("")
    lines.append(
        f"Multi-timeframe read: **{verdict}** "
        f"(confidence: {alignment.get('confidence', 'n/a')}) — {alignment.get('note', '')}"
    )
    lines.append("")
    lines.append("| Timeframe | Trend | RSI | ATR (pips) | Range position | Range width |")
    lines.append("| --- | --- | --- | --- | --- | --- |")

    for tf_name, read in pair.get("timeframes", {}).items():
        trend = read["trend"]
        momentum = read["momentum"]
        volatility = read["volatility"]
        levels = read["levels"]
        position = levels.get("position_in_range")
        lines.append(
            f"| {tf_name} "
            f"| {_ARROWS.get(trend['direction'], '')} {trend['direction']} "
            f"| {_fmt(momentum.get('rsi'))} "
            f"| {_fmt(volatility.get('atr_pips'))} "
            f"| {_fmt(None if position is None else position * 100, 0, '%')} "
            f"| {_fmt(levels.get('range_pips'), 0)} |"
        )

    lines.append("")

    for tf_name, read in pair.get("timeframes", {}).items():
        levels = read["levels"]
        lines.append(
            f"- **{tf_name}**: {read['trend']['note']}. {read['momentum']['note']}. "
            f"{read['volatility']['note']}. High {levels.get('recent_high', 'n/a')}, "
            f"low {levels.get('recent_low', 'n/a')}."
        )
        for warning in read.get("warnings", []):
            lines.append(f"  - note: {warning}")

    lines.append("")
    sessions = pair.get("relevant_sessions") or []
    if sessions:
        lines.append(f"Most active during: {', '.join(sessions)}")
        lines.append("")

    return lines


def render_markdown(payload: Dict[str, Any]) -> str:
    """Render the full report."""
    generated = payload.get("generated_at") or datetime.now(timezone.utc).isoformat()

    lines: List[str] = [
        "# Daily Forex Analysis",
        "",
        f"Generated: {generated}",
        f"Market status: {payload.get('session_summary', 'unknown')}",
        "",
    ]

    provider_status = payload.get("provider_status") or {}
    if provider_status:
        active = [name for name, state in provider_status.items() if state == "available"]
        lines.append(f"Data providers available: {', '.join(active) if active else 'none'}")
        lines.append("")

    commentary = payload.get("commentary")
    if commentary:
        lines.extend(["## Analyst commentary", "", commentary, ""])
    else:
        lines.extend([
            "## Analyst commentary",
            "",
            "_LLM commentary disabled or unavailable — showing computed analysis only._",
            "",
        ])

    lines.extend(["## Pairs", ""])
    for pair in payload.get("pairs", []):
        lines.extend(_render_pair_section(pair))

    failures = [p for p in payload.get("pairs", []) if p.get("error")]
    if failures:
        lines.extend(["## Failures", ""])
        for pair in failures:
            lines.append(f"- {pair['pretty']}: {pair['error']}")
        lines.append("")

    lines.extend(["---", "", f"_{_DISCLAIMER}_", ""])
    return "\n".join(lines)


def render(payload: Dict[str, Any], fmt: str = "markdown") -> str:
    fmt = (fmt or "markdown").lower()
    if fmt == "json":
        return render_json(payload)
    if fmt in ("markdown", "md"):
        return render_markdown(payload)
    raise ValueError(f"unsupported report format: {fmt!r} (use 'markdown' or 'json')")


def telegram_summary(payload: Dict[str, Any], limit: int = 3800) -> str:
    """Compact plain-text summary sized for a Telegram message."""
    lines = [
        "Daily Forex Analysis",
        payload.get("session_summary", ""),
        "",
    ]

    for pair in payload.get("pairs", []):
        if pair.get("error"):
            lines.append(f"{pair['pretty']}: unavailable ({pair['error'][:60]})")
            continue

        alignment = pair.get("alignment", {})
        daily = pair.get("timeframes", {}).get("D1") or {}
        atr_pips = (daily.get("volatility") or {}).get("atr_pips")
        lines.append(
            f"{pair['pretty']}: {alignment.get('verdict', 'n/a')} "
            f"({alignment.get('confidence', 'n/a')}) @ "
            f"{pair.get('last_price_display', 'n/a')}"
            + (f", D1 ATR {atr_pips:.0f} pips" if atr_pips is not None else "")
        )

    commentary = payload.get("commentary")
    if commentary:
        lines.extend(["", commentary])

    text = "\n".join(lines).strip()
    if len(text) > limit:
        text = text[: limit - 3].rstrip() + "..."
    return text
