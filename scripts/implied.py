#!/usr/bin/env python3
"""定价反推：当前 EV 隐含多少增长，以及不同增速对应多少 EV。

用法:
    python implied.py --ev 241.40 --fcf0 1.80 --price 239.34 --shares 1.0261
    python implied.py --ev 241.40 --fcf0 1.80 --price 239.34 --shares 1.0261 --rev-next 7.38

输出四块：
  1. 反向 DCF：9/10/11/12% 折现率 × 2/3% 终值增长 → 隐含 10 年 FCF CAGR
  2. 敏感度：给定增速 → 合理 EV 与当前 EV 的偏离
  3. 情景价位：不同 PS 乘以下一财年营收 → 股价与回报
  4. 共识隐含 EPS：forward PE 反推，和公司指引对照

单位统一用十亿美元；股价用绝对价格。
"""

from __future__ import annotations

import argparse


def ev_of(g: float, fcf0: float, n: int, r: float, tg: float) -> float:
    """FCF 以 g 增长 n 年、之后按 tg 永续，折现到今天的 EV。"""
    pv, f = 0.0, fcf0
    for t in range(1, n + 1):
        f *= 1 + g
        pv += f / (1 + r) ** t
    terminal = f * (1 + tg) / (r - tg)
    return pv + terminal / (1 + r) ** n


def implied_growth(target_ev: float, fcf0: float, n: int, r: float, tg: float) -> float:
    lo, hi = 0.0, 2.0
    for _ in range(300):
        mid = (lo + hi) / 2
        if ev_of(mid, fcf0, n, r, tg) < target_ev:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def main() -> None:
    ap = argparse.ArgumentParser(description="反向 DCF 与情景估值")
    ap.add_argument("--ev", type=float, required=True, help="当前企业价值（十亿）")
    ap.add_argument("--fcf0", type=float, required=True, help="基年 FCF（十亿）")
    ap.add_argument("--price", type=float, help="现价")
    ap.add_argument("--shares", type=float, help="股数（十亿）")
    ap.add_argument("--rev-next", type=float, help="下一财年营收预期（十亿），用于情景价位")
    ap.add_argument("--years", type=int, default=10)
    ap.add_argument("--pe-forward", type=float, help="第三方 forward PE，用于反推 EPS")
    ap.add_argument("--eps-guide", type=float, help="公司指引 EPS 中值，用于对照")
    args = ap.parse_args()

    print(f"当前 EV {args.ev:.2f}B · 基年 FCF {args.fcf0:.2f}B · 期限 {args.years} 年")
    print()
    print("=== 1. 反向 DCF：隐含 10 年 FCF 复合增速 ===")
    print("| 折现率 | 终值增长 | 隐含 FCF CAGR |")
    print("|---|---|---|")
    base = None
    for r in (0.09, 0.10, 0.11, 0.12):
        for tg in (0.02, 0.03):
            g = implied_growth(args.ev, args.fcf0, args.years, r, tg)
            if r == 0.10 and tg == 0.03:
                base = g
            print(f"| {r:.0%} | {tg:.0%} | {g:.1%} |")
    print()

    print("=== 2. 敏感度（折现率 10%、终值增长 3%）===")
    print("| FCF CAGR | 合理 EV | vs 当前 |")
    print("|---|---|---|")
    for g in (0.15, 0.20, 0.25, 0.30, 0.35, 0.40):
        ev = ev_of(g, args.fcf0, args.years, 0.10, 0.03)
        print(f"| {g:.0%} | {ev:.0f}B | {ev / args.ev - 1:+.0%} |")
    if base:
        print(f"\n基准隐含增速 {base:.1%}（10% 折现、3% 终值）")
    print()

    if args.price and args.shares and args.rev_next:
        print("=== 3. 情景价位（PS × 下一财年营收）===")
        print("| 情景 | PS | 市值 | 股价 | 回报 |")
        print("|---|---|---|---|---|")
        for label, ps in (("深熊 20x", 20), ("熊 25x", 25), ("基准 32x", 32), ("牛 45x", 45)):
            cap = ps * args.rev_next
            px = cap / args.shares
            print(f"| {label} | {ps}x | {cap:.0f}B | ${px:.0f} | {px / args.price - 1:+.0%} |")
        print()

    if args.pe_forward and args.price:
        eps = args.price / args.pe_forward
        print("=== 4. 共识隐含 EPS ===")
        line = f"forward PE {args.pe_forward:.1f}x → 隐含 EPS ${eps:.2f}"
        if args.eps_guide:
            line += f"，较公司指引 ${args.eps_guide:.2f} 高 {eps / args.eps_guide - 1:+.1%}"
        print(line)
        print("若共识目标价≈现价而 EPS 在增长，则共识隐含倍数收缩——这是报告里最值得写的一句。")


if __name__ == "__main__":
    main()
