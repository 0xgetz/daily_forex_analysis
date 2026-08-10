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


def render_csv(payload: Dict[str, Any]) -> str:
    """Flatten every timeframe read into a CSV row."""
    import csv
    import io

    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow([
        "symbol", "timeframe", "trend", "rsi", "macd_histogram",
        "atr_pips", "atr_percentile", "range_position_pct", "range_pips",
        "last_close", "change_pips", "source", "verdict", "confidence",
    ])

    for pair in payload.get("pairs", []):
        if pair.get("error"):
            continue
        alignment = pair.get("alignment", {})
        for tf_name, read in pair.get("timeframes", {}).items():
            trend = read.get("trend", {})
            momentum = read.get("momentum", {})
            volatility = read.get("volatility", {})
            levels = read.get("levels", {})
            writer.writerow([
                pair.get("pretty", ""),
                tf_name,
                trend.get("direction", ""),
                momentum.get("rsi", ""),
                momentum.get("macd_histogram", ""),
                volatility.get("atr_pips", ""),
                volatility.get("atr_percentile", ""),
                (levels.get("position_in_range") or 0) * 100,
                levels.get("range_pips", ""),
                read.get("last_close", ""),
                read.get("change_pips", ""),
                pair.get("source", ""),
                alignment.get("verdict", ""),
                alignment.get("confidence", ""),
            ])
    return out.getvalue()


def render_html(payload: Dict[str, Any]) -> str:
    """Self-contained HTML report with embedded CSS."""
    generated = payload.get("generated_at") or datetime.now(timezone.utc).isoformat()
    session = payload.get("session_summary", "unknown")

    rows = []
    for pair in payload.get("pairs", []):
        if pair.get("error"):
            rows.append(
                f'<tr class="error"><td>{pair.get("pretty","")}</td>'
                f'<td colspan="12">{pair.get("error","")}</td></tr>'
            )
            continue
        alignment = pair.get("alignment", {})
        verdict = alignment.get("verdict", "unknown")
        verdict_class = {
            "up": "up", "down": "down", "sideways": "sideways", "conflicted": "conflicted",
        }.get(verdict, "sideways")
        arrow = _ARROWS.get(verdict, "")

        for tf_name, read in pair.get("timeframes", {}).items():
            trend = read.get("trend", {})
            momentum = read.get("momentum", {})
            volatility = read.get("volatility", {})
            levels = read.get("levels", {})
            pos = levels.get("position_in_range")
            pos_pct = f"{pos*100:.0f}%" if pos is not None else "n/a"

            trend_arrow = _ARROWS.get(trend.get("direction"), "")
            rows.append(
                f'<tr>'
                f'<td class="symbol">{pair.get("pretty","")}</td>'
                f'<td>{tf_name}</td>'
                f'<td class="{verdict_class}">{arrow} {trend.get("direction","")}</td>'
                f'<td>{_fmt(momentum.get("rsi"))}</td>'
                f'<td>{_fmt(volatility.get("atr_pips"))}</td>'
                f'<td>{_fmt(volatility.get("atr_percentile"), 0)}</td>'
                f'<td>{pos_pct}</td>'
                f'<td>{_fmt(levels.get("range_pips"), 0)}</td>'
                f'<td>{read.get("last_close","")}</td>'
                f'<td>{_fmt(read.get("change_pips"))}</td>'
                f'<td>{pair.get("source","")}</td>'
                f'<td class="{verdict_class}">{arrow} {verdict}</td>'
                f'<td>{alignment.get("confidence","")}</td>'
                f'</tr>'
            )

    commentary = payload.get("commentary") or ""
    if commentary:
        commentary_html = f'<div class="commentary"><h2>Analyst Commentary</h2><p>{commentary}</p></div>'
    else:
        commentary_html = '<div class="commentary muted"><em>LLM commentary disabled or unavailable.</em></div>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Daily Forex Analysis</title>
<style>
  :root {{
    --bg: #0d1117; --fg: #c9d1d9; --muted: #8b949e; --border: #30363d;
    --up: #3fb950; --down: #f85149; --sideways: #d29922; --conflicted: #f85149;
    --accent: #58a6ff;
  }}
  * {{ box-sizing: border-box; }}
  body {{ background: var(--bg); color: var(--fg); font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; margin: 0; padding: 2rem; }}
  h1 {{ border-bottom: 1px solid var(--border); padding-bottom: .5rem; }}
  .meta {{ color: var(--muted); margin-bottom: 1.5rem; }}
  table {{ border-collapse: collapse; width: 100%; margin: 1.5rem 0; font-size: .9rem; }}
  th, td {{ border: 1px solid var(--border); padding: .5rem .75rem; text-align: left; }}
  th {{ background: #161b22; font-weight: 600; }}
  tr:hover {{ background: #161b22; }}
  .symbol {{ font-weight: 600; }}
  .up {{ color: var(--up); }} .down {{ color: var(--down); }}
  .sideways {{ color: var(--sideways); }} .conflicted {{ color: var(--conflicted); }}
  .error td {{ color: var(--conflicted); font-style: italic; }}
  .commentary {{ background: #161b22; border: 1px solid var(--border); border-radius: 6px; padding: 1rem 1.5rem; margin: 1.5rem 0; }}
  .muted {{ color: var(--muted); }}
  footer {{ margin-top: 2rem; padding-top: 1rem; border-top: 1px solid var(--border); color: var(--muted); font-size: .85rem; }}
</style>
</head>
<body>
<h1>Daily Forex Analysis</h1>
<div class="meta">
  Generated: {generated}<br>
  Market status: {session}
</div>
{commentary_html}
<h2>Pairs</h2>
<table>
<thead>
<tr>
  <th>Symbol</th><th>TF</th><th>Trend</th><th>RSI</th><th>ATR (pips)</th><th>ATR %ile</th>
  <th>Range pos</th><th>Range (pips)</th><th>Close</th><th>Chg (pips)</th>
  <th>Source</th><th>Verdict</th><th>Confidence</th>
</tr>
</thead>
<tbody>
{''.join(rows)}
</tbody>
</table>
<footer>{_DISCLAIMER}</footer>
</body>
</html>"""


def render(payload: Dict[str, Any], fmt: str = "markdown") -> str:
    fmt = (fmt or "markdown").lower()
    if fmt == "json":
        return render_json(payload)
    if fmt == "csv":
        return render_csv(payload)
    if fmt == "html":
        return render_html(payload)
    if fmt in ("markdown", "md"):
        return render_markdown(payload)
    raise ValueError(f"unsupported report format: {fmt!r} (use 'markdown', 'json', 'csv' or 'html')")


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
