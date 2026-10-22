#!/usr/bin/env python3
"""把一次 run 的分节 markdown 拼成 complete_report.md 与自包含的 complete_report.html。

用法:
    python build_report.py runs/CRWD_2026-10-22
    python build_report.py runs/CRWD_2026-10-22 --title "CrowdStrike (CRWD)"

零依赖：内置一个够用的 markdown 子集渲染器（标题/粗斜体/表格/列表/引用/分隔线）。
"""

from __future__ import annotations

import argparse
import html
import re
import sys
from datetime import datetime
from pathlib import Path

# 报告章节顺序：(heading, [(label, relative path)])
SECTIONS = (
    ("I. Analyst Team Reports", [
        ("Market Analyst", "1_analysts/market.md"),
        ("Sentiment Analyst", "1_analysts/sentiment.md"),
        ("News Analyst", "1_analysts/news.md"),
        ("Fundamentals Analyst", "1_analysts/fundamentals.md"),
    ]),
    ("II. Research Team Decision", [
        ("Bull Researcher", "2_research/bull.md"),
        ("Bear Researcher", "2_research/bear.md"),
        ("Research Manager", "2_research/manager.md"),
    ]),
    ("III. Trading Team Plan", [
        ("Trader", "3_trading/trader.md"),
    ]),
    ("IV. Risk Management Team Decision", [
        ("Aggressive Analyst", "4_risk/aggressive.md"),
        ("Conservative Analyst", "4_risk/conservative.md"),
        ("Neutral Analyst", "4_risk/neutral.md"),
    ]),
    ("V. Portfolio Manager Decision", [
        ("Portfolio Manager", "5_portfolio/decision.md"),
    ]),
)

RATING_RE = re.compile(
    r"[\s*_#]*(?:final|our|overall)?[\s*_]*rating[\s*_]*[:\-\u2010-\u2015][\s*]*(buy|overweight|hold|underweight|sell)\b",
    re.IGNORECASE,
)

# 中文合成报告里评级常写成「**评级 Underweight**」，分隔符可能省略
RATING_CN_RE = re.compile(
    r"评级[\s*_]*[:\-\u2010-\u2015]?[\s*_]*(buy|overweight|hold|underweight|sell)\b",
    re.IGNORECASE,
)


def parse_rating(text: str) -> str:
    """读终裁第一行的 **Rating**: X；读不到就找全文唯一一致的 Rating 行；否则 REVIEW。"""
    lines = [ln for ln in text.splitlines() if ln.strip()]
    found: list[str] = []
    for ln in lines:
        m = RATING_RE.match(ln)
        if m:
            found.append(m.group(1).capitalize())
    if not found:
        return "REVIEW"
    first = found[0]
    if all(f == first for f in found):
        return first
    return "REVIEW"


def collect(run_dir: Path) -> tuple[list[tuple[str, list[tuple[str, str]]]], str]:
    parts = []
    for heading, agents in SECTIONS:
        written = []
        for label, rel in agents:
            path = run_dir / rel
            if path.exists():
                text = path.read_text(encoding="utf-8").strip()
                if text:
                    written.append((label, text))
        if written:
            parts.append((heading, written))
    decision = (run_dir / "5_portfolio" / "decision.md")
    rating = parse_rating(decision.read_text(encoding="utf-8")) if decision.exists() else "REVIEW"
    return parts, rating


def write_markdown(run_dir: Path, ticker: str, date: str, parts, rating: str) -> Path:
    header = [
        f"# Trading Analysis Report: {ticker}",
        "",
        f"- Analysis date: {date}",
        f"- Rating: {rating}",
        f"- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "- Workflow: trading-agents-workflow（TradingAgents 复刻）",
        "- Analysts: market, sentiment, news, fundamentals",
        "- Debate rounds: research 1, risk 1",
    ]
    body = []
    for heading, written in parts:
        body.append(f"## {heading}")
        for label, text in written:
            body.append(f"### {label}")
            body.append(text)
    out = run_dir / "complete_report.md"
    out.write_text("\n".join(header) + "\n\n" + "\n\n".join(body) + "\n", encoding="utf-8")
    return out


# ---------------------------------------------------------------- markdown 子集

def _inline(text: str) -> str:
    text = html.escape(text, quote=False)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<![\*\w])\*([^*\n]+)\*(?![\*\w])", r"<em>\1</em>", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    return text


def _table(rows: list[str]) -> str:
    def cells(line: str) -> list[str]:
        line = line.strip()
        if line.startswith("|"):
            line = line[1:]
        if line.endswith("|"):
            line = line[:-1]
        return [c.strip() for c in line.split("|")]

    head = cells(rows[0])
    body = [cells(r) for r in rows[2:]]
    out = ["<div class='tw'><table><thead><tr>"]
    out += [f"<th>{_inline(c)}</th>" for c in head]
    out.append("</tr></thead><tbody>")
    for r in body:
        out.append("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in r) + "</tr>")
    out.append("</tbody></table></div>")
    return "".join(out)


def md_to_html(text: str) -> str:
    lines = text.splitlines()
    out: list[str] = []
    i = 0
    in_list: str | None = None

    def close_list():
        nonlocal in_list
        if in_list:
            out.append(f"</{in_list}>")
            in_list = None

    while i < len(lines):
        ln = lines[i]
        s = ln.strip()

        if not s:
            close_list()
            i += 1
            continue

        # 表格：连续的 | 行
        if s.startswith("|") and i + 1 < len(lines) and re.match(r"^\|?[\s:\-|]+\|?$", lines[i + 1].strip()):
            close_list()
            block = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                block.append(lines[i])
                i += 1
            out.append(_table(block))
            continue

        m = re.match(r"^(#{1,6})\s+(.*)$", s)
        if m:
            close_list()
            level = len(m.group(1))
            title = m.group(2).strip()
            anchor = re.sub(r"[^\w\u4e00-\u9fff]+", "-", title).strip("-").lower()
            out.append(f'<h{level} id="{anchor}">{_inline(title)}</h{level}>')
            i += 1
            continue

        if re.match(r"^(\*\s*\*\s*\*|-{3,}|_{3,})$", s):
            close_list()
            out.append("<hr>")
            i += 1
            continue

        if s.startswith(">"):
            close_list()
            buf = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                buf.append(lines[i].strip().lstrip(">").strip())
                i += 1
            out.append("<blockquote>" + "<br>".join(_inline(b) for b in buf) + "</blockquote>")
            continue

        if re.match(r"^[-*+]\s+", s):
            if in_list != "ul":
                close_list()
                out.append("<ul>")
                in_list = "ul"
            out.append(f"<li>{_inline(re.sub(r'^[-*+]\\s+', '', s))}</li>")
            i += 1
            continue

        if re.match(r"^\d+[.)]\s+", s):
            if in_list != "ol":
                close_list()
                out.append("<ol>")
                in_list = "ol"
            out.append(f"<li>{_inline(re.sub(r'^\\d+[.)]\\s+', '', s))}</li>")
            i += 1
            continue

        close_list()
        buf = []
        while i < len(lines) and lines[i].strip() and not re.match(
            r"^(#{1,6}\s|\||>|[-*+]\s|\d+[.)]\s)", lines[i].strip()
        ):
            buf.append(lines[i].strip())
            i += 1
        out.append("<p>" + "<br>".join(_inline(b) for b in buf) + "</p>")

    close_list()
    return "\n".join(out)


CSS = """
:root{--fg:#1f2328;--mut:#5b6470;--line:#e3e6ea;--bg:#fff;--soft:#f6f8fa;
--up:#c0392b;--down:#1e8449;--hold:#6b7280;--accent:#1f4e79}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
font:15px/1.75 -apple-system,BlinkMacSystemFont,"PingFang SC","Helvetica Neue",Arial,sans-serif}
.wrap{display:flex;gap:36px;max-width:1180px;margin:0 auto;padding:32px 24px 80px}
nav{position:sticky;top:24px;align-self:flex-start;width:210px;flex:0 0 210px;
font-size:12.5px;line-height:1.6;border-right:1px solid var(--line);padding-right:16px;max-height:88vh;overflow:auto}
nav a{display:block;color:var(--mut);text-decoration:none;padding:3px 0}
nav a:hover{color:var(--accent)}
nav .n1{font-weight:600;color:var(--fg);margin-top:10px}
main{flex:1;min-width:0}
h1{font-size:26px;margin:0 0 6px;letter-spacing:-.3px}
h2{font-size:19px;margin:44px 0 14px;padding-bottom:8px;border-bottom:1px solid var(--line)}
h3{font-size:15.5px;margin:26px 0 10px;color:var(--accent)}
h4{font-size:14px;margin:18px 0 8px}
p{margin:10px 0}
ul,ol{margin:10px 0;padding-left:22px}
li{margin:5px 0}
hr{border:0;border-top:1px solid var(--line);margin:26px 0}
blockquote{margin:12px 0;padding:8px 14px;border-left:3px solid var(--line);
background:var(--soft);color:var(--mut);border-radius:0 4px 4px 0}
code{background:var(--soft);padding:1px 5px;border-radius:4px;font-size:12.5px;
font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
a{color:var(--accent)}
.tw{overflow-x:auto;margin:14px 0}
table{border-collapse:collapse;width:100%;font-size:13px}
th,td{border:1px solid var(--line);padding:7px 10px;text-align:left;vertical-align:top}
th{background:var(--soft);font-weight:600;white-space:nowrap}
tbody tr:nth-child(even){background:#fafbfc}
.meta{color:var(--mut);font-size:13px;margin:0 0 22px}
.badge{display:inline-block;padding:2px 10px;border-radius:999px;font-size:12.5px;
font-weight:600;color:#fff;vertical-align:2px}
.b-up{background:var(--up)}.b-down{background:var(--down)}.b-hold{background:var(--hold)}
.b-rev{background:#b45309}
@media print{
nav{display:none}.wrap{display:block;max-width:none;padding:0}
h2{page-break-after:avoid}table,.tw{page-break-inside:avoid}
}
@media (max-width:860px){.wrap{display:block}nav{position:static;width:auto;flex:none;
border-right:0;border-bottom:1px solid var(--line);padding:0 0 12px;margin-bottom:20px;max-height:none}}
"""


def write_html(run_dir: Path, ticker: str, date: str, parts, rating: str) -> Path:
    cls = {"Buy": "b-up", "Overweight": "b-up", "Hold": "b-hold",
           "Underweight": "b-down", "Sell": "b-down"}.get(rating, "b-rev")

    toc, body = [], []
    for heading, written in parts:
        anchor = re.sub(r"[^\w\u4e00-\u9fff]+", "-", heading).strip("-").lower()
        toc.append(f'<a class="n1" href="#{anchor}">{html.escape(heading)}</a>')
        body.append(f'<h2 id="{anchor}">{html.escape(heading)}</h2>')
        for label, text in written:
            body.append(f"<h3>{html.escape(label)}</h3>")
            body.append(md_to_html(text))

    doc = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(ticker)} · {date} 投研报告</title>
<style>{CSS}</style></head><body><div class="wrap">
<nav>{''.join(toc)}</nav>
<main>
<h1>{html.escape(ticker)} <span class="badge {cls}">{rating}</span></h1>
<p class="meta">分析日 {date} · 生成于 {datetime.now().strftime('%Y-%m-%d %H:%M')} ·
trading-agents-workflow（TradingAgents 复刻）· 仅供研究，不构成投资建议</p>
{''.join(body)}
</main></div></body></html>"""
    out = run_dir / "complete_report.html"
    out.write_text(doc, encoding="utf-8")
    return out


def render_single(md_path: Path, out_path: Path, title: str, rating: str = "") -> Path:
    """把一份合成好的 report.md 渲染成自包含 HTML（v2 交付物）。"""
    text = md_path.read_text(encoding="utf-8")
    body = md_to_html(text)

    toc = []
    for m in re.finditer(r"^(#{2})\s+(.+)$", text, re.MULTILINE):
        heading = m.group(2).strip()
        anchor = re.sub(r"[^\w\u4e00-\u9fff]+", "-", heading).strip("-").lower()
        toc.append(f'<a class="n1" href="#{anchor}">{html.escape(heading)}</a>')

    cls = {"Buy": "b-up", "Overweight": "b-up", "Hold": "b-hold",
           "Underweight": "b-down", "Sell": "b-down"}.get(rating, "")
    badge = f' <span class="badge {cls}">{rating}</span>' if cls else ""

    doc = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)} · 投研报告</title>
<style>{CSS}</style></head><body><div class="wrap">
<nav>{''.join(toc)}</nav>
<main>
<h1>{html.escape(title)}{badge}</h1>
<p class="meta">生成于 {datetime.now().strftime('%Y-%m-%d %H:%M')} ·
trading-agents-workflow · 仅供研究，不构成投资建议</p>
{body}
</main></div></body></html>"""
    out_path.write_text(doc, encoding="utf-8")
    return out_path


def main() -> None:
    ap = argparse.ArgumentParser(description="拼装或渲染投研报告")
    ap.add_argument("run_dir", nargs="?", help="run 目录（v1 拼装模式）")
    ap.add_argument("--md", help="单份 report.md（v2 渲染模式）")
    ap.add_argument("--out", help="--md 模式下的输出 html 路径")
    ap.add_argument("--title", default=None, help="页面标题")
    ap.add_argument("--ticker", default=None)
    ap.add_argument("--date", default=None)
    args = ap.parse_args()

    if args.md:
        md_path = Path(args.md).expanduser().resolve()
        if not md_path.is_file():
            sys.exit(f"文件不存在: {md_path}")
        out = Path(args.out).expanduser().resolve() if args.out else md_path.with_suffix(".html")
        title = args.title or md_path.stem
        rating = ""
        text = md_path.read_text(encoding="utf-8")
        m = RATING_RE.search(text) or RATING_CN_RE.search(text)
        if m:
            rating = m.group(1).capitalize()
        path = render_single(md_path, out, title, rating)
        print(f"rating : {rating or '未识别'}")
        print(f"html   : {path}")
        return

    if not args.run_dir:
        sys.exit("需要 run_dir，或用 --md 指定单份报告")

    run_dir = Path(args.run_dir).expanduser().resolve()
    if not run_dir.is_dir():
        sys.exit(f"目录不存在: {run_dir}")

    stem = run_dir.name
    ticker = args.ticker or (stem.rsplit("_", 1)[0] if "_" in stem else stem)
    date = args.date or (stem.rsplit("_", 1)[1] if "_" in stem else datetime.now().strftime("%Y-%m-%d"))

    parts, rating = collect(run_dir)
    if not parts:
        sys.exit("没有任何分节文件，先跑完分析师阶段")

    md = write_markdown(run_dir, ticker, date, parts, rating)
    html_path = write_html(run_dir, ticker, date, parts, rating)
    print(f"rating : {rating}")
    print(f"md     : {md}")
    print(f"html   : {html_path}")


if __name__ == "__main__":
    main()
