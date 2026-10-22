#!/usr/bin/env python3
"""为一次多智能体投研分析建目录骨架，并初始化决策记忆。

用法:
    python init_run.py NVDA 2026-10-22
    python init_run.py 600519.SS 2026-10-22 --analysts market,fundamentals --out ~/research
    python init_run.py BTC-USD 2026-10-22 --rounds 2

只建目录和空文件，不写任何内容——内容由各阶段角色自己写。
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

HOME = Path.home()
MEMORY_DIR = HOME / ".workbuddy-ai" / "trading-workflow"

# 与原版 report tree 的 1_analysts / 2_research / ... 对齐
ANALYST_FILES = {
    "market": "market.md",
    "sentiment": "sentiment.md",
    "news": "news.md",
    "fundamentals": "fundamentals.md",
}

# 交易所后缀 -> (市场名, 基准)
MARKETS = [
    (r"\.SS$|\.SZ$", "A股", "000300.SS"),
    (r"\.HK$", "港股", "^HSI"),
    (r"\.T$", "日股", "^N225"),
    (r"\.L$", "英股", "^FTSE"),
    (r"\.NS$|\.BO$", "印度", "^NSEI"),
    (r"-USD$", "加密", "BTC-USD"),
    (r"\.AX$", "澳股", "^AXJO"),
    (r"\.TO$", "加股", "^GSPTSE"),
]


def resolve_market(ticker: str) -> tuple[str, str]:
    upper = ticker.upper()
    for pattern, name, benchmark in MARKETS:
        if re.search(pattern, upper):
            return name, benchmark
    return "美股", "SPY"


def parse_analysts(raw: str) -> list[str]:
    keys = [k.strip().lower() for k in raw.split(",") if k.strip()]
    bad = [k for k in keys if k not in ANALYST_FILES]
    if bad:
        sys.exit(f"未知分析师: {', '.join(bad)}；可选: {', '.join(ANALYST_FILES)}")
    if not keys:
        sys.exit("至少选一个分析师")
    return keys


def init_memory() -> bool:
    """建记忆目录与空的 decisions.md；返回是否新建。"""
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    decisions = MEMORY_DIR / "decisions.md"
    if decisions.exists():
        return False
    decisions.write_text(
        "# 决策日志\n\n"
        "格式与结算规则见 skill `trading-agents-workflow` 的 "
        "`references/memory-protocol.md`。只追加，不改历史。\n\n",
        encoding="utf-8",
    )
    return True


def main() -> None:
    ap = argparse.ArgumentParser(description="建一次投研分析的目录骨架")
    ap.add_argument("ticker", help="标的代码，如 NVDA / 0700.HK / 600519.SS")
    ap.add_argument("date", nargs="?", default=datetime.now().strftime("%Y-%m-%d"),
                    help="分析日期 YYYY-MM-DD，默认今天")
    ap.add_argument("--analysts", default="market,sentiment,news,fundamentals",
                    help="逗号分隔，默认四个全开")
    ap.add_argument("--rounds", type=int, default=1,
                    help="辩论轮数，0 表示跳过辩论（快档）")
    ap.add_argument("--out", default="runs", help="输出根目录，默认 ./runs")
    args = ap.parse_args()

    ticker = args.ticker.strip().upper()
    try:
        datetime.strptime(args.date, "%Y-%m-%d")
    except ValueError:
        sys.exit(f"日期格式不对: {args.date}，要 YYYY-MM-DD")

    analysts = parse_analysts(args.analysts)
    market, benchmark = resolve_market(ticker)

    run_dir = Path(args.out).expanduser() / f"{ticker.replace('/', '-')}_{args.date}"
    if run_dir.exists():
        sys.exit(f"目录已存在，换日期或先清理: {run_dir}")

    dirs = ["1_analysts", "2_research", "3_trading", "4_risk", "5_portfolio"]
    for d in dirs:
        (run_dir / d).mkdir(parents=True, exist_ok=True)

    for key in analysts:
        (run_dir / "1_analysts" / ANALYST_FILES[key]).touch()

    if args.rounds > 0:
        for f in ("bull.md", "bear.md"):
            (run_dir / "2_research" / f).touch()
        for f in ("aggressive.md", "conservative.md", "neutral.md"):
            (run_dir / "4_risk" / f).touch()
    # 定价反推任何档位都要做，是报告骨架
    (run_dir / "2_research" / "pricing.md").touch()
    (run_dir / "2_research" / "manager.md").touch()
    (run_dir / "3_trading" / "trader.md").touch()
    (run_dir / "5_portfolio" / "decision.md").touch()

    created_memory = init_memory()

    print(f"run_dir   : {run_dir}")
    print(f"ticker    : {ticker}")
    print(f"market    : {market}")
    print(f"benchmark : {benchmark}")
    print(f"analysts  : {', '.join(analysts)}")
    print(f"rounds    : {args.rounds}" + ("（跳过辩论）" if args.rounds == 0 else ""))
    print(f"memory    : {MEMORY_DIR / 'decisions.md'}" + ("（新建）" if created_memory else ""))
    print()
    print("下一步：按 SKILL.md 的 Phase 1 起子 agent 写 1_analysts/*.md")
    print("        Phase 2.5 用 implied.py 做定价反推，写 2_research/pricing.md（必做）")


if __name__ == "__main__":
    main()
