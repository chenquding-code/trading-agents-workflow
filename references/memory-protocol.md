# 决策记忆协议

对应原版 `tradingagents/memory/`：决策日志 + 事后结算 + 教训回注。原版靠这套机制让第 N 次分析读到第 N-1 次的错。

## 位置

```
~/.workbuddy-ai/trading-workflow/
├── decisions.md      决策日志（追加，不覆盖）
└── lessons.md        沉淀后的教训（定期从 decisions 提炼）
```

跨项目共享：同一个标的在不同 workspace 里分析，记忆是同一份。

## decisions.md 格式

每条决策一个块，`---` 分隔。**只追加，不改历史**（结算时新增 `settled` 字段，不改原字段）。

```markdown
## <ticker> · <analysis_date>
- rating: Buy | Overweight | Hold | Underweight | Sell
- benchmark: SPY
- entry_price: 189.5        （交易员给的，没有就写 null）
- stop_loss: 172.0
- status: pending
- thesis_digest: <一句话，只写决定结论的核心论点>
- run_dir: runs/NVDA_2026-10-22

---
```

结算后追加（不改上面的行）：

```markdown
- status: settled
- settled_on: 2026-10-29
- raw_return_5d: +3.2%
- alpha_5d: +1.1%
- lesson: <2-4 句，见 roles.md「事后反思」>
```

## 结算规则

1. **窗口**：分析日之后**第一个收盘**起算，往后 5 个交易日。分析日在收盘前发的，就从当天收盘算。
2. **收益**：`(第5日收盘 / 起算日收盘 - 1)`，用前复权价。
3. **alpha**：绝对收益 − 同期基准收益。基准按 data-checklist.md 的市场对照表取。
4. **窗口不足 5 天**：不结算，保持 pending，下次再试。不要用 2 天的结果假装 5 天。
5. **窗口过短不足以评判论点**：教训里直接写出来，不要硬下结论。原版专门为此加了一句"the window may be shorter than the horizon the decision was written for"，照抄这个自觉。
6. **标的退市/停牌**：标 `status: void`，注明原因。

## 教训回注

组合经理阶段（Phase 6）读取，组装成 `past_context`：

```
【同标的】<ticker> 在 <date> 给出 <rating>，5 日超额 <-2.1%>。教训：<lesson>
【跨标的】<其他 ticker> 的教训：<lesson>（仅当主题相关时才注入）
```

注入规则：
- 同标的教训**全部**注入（最多最近 5 条）
- 跨标的教训只注入与当前标的相关主题的（同一行业、同一类风险），最多 3 条
- 总长度控制在 800 字以内，超了就只保留最近的

## 提炼

`decisions.md` 超过 30 条时，把已 settled 的按主题（如"高位追涨""财报前建仓""周期股估值"）归并到 `lessons.md`，原文保留但标注 `archived`。`lessons.md` 每条教训一句话，附支撑案例数和平均 alpha。

## 禁止

- 不要为了让历史看起来准，回头改评级
- 不要在没有结算数据时编造 lesson
- 不要把 pending 的决策当成已实现的业绩引用
