# trading-agents-workflow

[![License: Apache 2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Derived from TradingAgents](https://img.shields.io/badge/derived%20from-TauricResearch%2FTradingAgents-8a2be2.svg)](https://github.com/TauricResearch/TradingAgents)
[![Python stdlib only](https://img.shields.io/badge/python-stdlib%20only-3776ab.svg)](scripts/)
[![Skill](https://img.shields.io/badge/format-WorkBuddy%20%2F%20Claude%20Skill-2ea44f.svg)](SKILL.md)

把 [TradingAgents](https://github.com/TauricResearch/TradingAgents) 的多智能体投研流程，改造成一份**可以直接给基金经理看**的投研报告。

原版是一套研究框架：11 个角色各自输出，按图顺序拼成一份长文档，读者自己提炼。这里保留同样的图，但只交付一份合成报告——主轴是两句话：**市场现在在为什么付钱**，以及**我们的判断和最新卖方共识差在哪**。

技术面从平级分析师降为执行附录。论点必须落在财务、竞争、定价上。

这是一个 [WorkBuddy](https://www.workbuddy.cn) / Claude Skill，也能当纯提示词工程参考读。

本仓库还收了第二个 skill：[`dolphin-research/`](dolphin-research/)。它是从海豚投研 2026 年全部中文原文里提炼的财报、个股、行业三套研究方法论（3419 条方法，280 张公司/行业卡片），配一个按编号检索的脚本。可以单独用，也可以给本工作流的各阶段供方法，见 [dolphin-research/README.md](dolphin-research/README.md)。

---

## 它和原版的区别

| | TradingAgents | 这里 |
|---|---|---|
| 交付物 | 11 个角色原文按图拼接（1700+ 行） | 一份九节合成报告（~300 行） |
| 技术面地位 | 平级分析师，可给方向判断 | 附录，只给止损位和减仓窗口，**禁止方向判断** |
| 报告主轴 | 各角色结论汇总 | 定价分解 + 共识偏离 |
| 数据源 | yfinance / SEC EDGAR / FRED / StockTwits / Reddit | 公开检索 + 官方披露；A股/港股情绪源换雪球、股吧、东财 |
| 角色隔离 | 独立 LLM 调用，天然隔离 | 单模型扮演，靠「一阶段一文件」硬规则 |
| 回测 | ticker × date 网格回测 | 无。只有决策记忆的事后结算 |

一句话：**原版是「多智能体怎么协作」的答案，这里是「多智能体该产出什么」的答案。**

---

## 工作流

```
                    ┌─ 基本面 ─┐
START ──┬─ 新闻宏观 ─┼─ 情绪面 ─┼──┐        （并行，各自独立上下文）
        ├─ 技术面 ──┘           │        技术面只供执行价位，不作论点
        └─ 记忆结算（pending 决策）│
                                  ▼
                        定价反推：倍数分解 + 反向 DCF + 共识隐含假设
                                  ▼
                        多空辩论  bull ⇄ bear  × N 轮
                                  ▼
                        研究经理裁决 → 五档评级 + 战略动作
                                  ▼
                        交易员计划 → Buy/Hold/Sell + 入场/止损/仓位
                                  ▼
                  三方风险辩论  激进 → 保守 → 中性  × N 轮
                                  ▼
                        组合经理终裁 → 五档评级（唯一对外结论）
                                  ▼
              合成 report.md / report.html + 写入决策记忆
```

**定价反推（Phase 2.5）是整份报告的骨架，任何成本档位都不能跳。**

它把"股价"翻译成"隐含预期"，三件事：

1. **倍数分解** — 最近一段涨跌，多少来自盈利预期、多少来自倍数。结论通常一句话：*"这轮 -18.5% 全部来自倍数，盈利预期一分没动"*。
2. **反向 DCF** — 当前 EV 隐含的十年 FCF 复合增速是多少；增速降到 X% 时合理 EV 低多少。
3. **共识隐含假设** — forward PE 反推 NTM EPS，和公司指引比。**如果共识目标价≈现价但 EPS 假设在增长，共识其实在算倍数收缩。** 这一条几乎每次都能挖出来，是报告最有信息量的段落。

---

## 报告结构

九节，全部小标题写成**陈述句结论**而不是名词短语——读者只看目录就该知道每节说什么。

```
结论                    四段：市场在交易什么 / 共识算完了 / 我们的差异 / 操作
多空辩论                三行表格：核心逻辑、这个逻辑的最大风险、何时验证
1. 市场现在在交易什么     倍数分解、叙事判断、三个估值锚
2. 价格里已经包含了什么   反向 DCF、敏感度、共识隐含假设
3. 卖方共识的拆解        评级分布、目标价、上调下调次数、四个可质疑的假设
4. 我们与共识的差异      逐条点名，不写"我们认为估值偏高"这种废话
5. 基本面               增速质量、现金流与 GAAP 的裂缝、资本配置、相对同业
6. 估值                 四情景加权，说明分布是正偏还是负偏
7. 验证节点             哪个数据点、什么时候、什么阈值
8. 什么会推翻我们        四条可观测条件
附录 A 执行参考          止损位、减仓窗口、仓位
附录 B 数据缺口与口径     未获取项逐条列出，不估算
```

示例：[CRWD 2026-10-22](examples/CRWD-2026-10-22-report.md)（附 [12 个角色的审计原文](examples/CRWD-2026-10-22/audit/)）。

---

## 安装

```bash
git clone https://github.com/chenquding-code/trading-agents-workflow.git \
  ~/.workbuddy-ai/skills/trading-agents-workflow
```

WorkBuddy 会自动发现 `SKILL.md`。之后在对话里说「用 TradingAgents 的方式分析 NVDA」就会触发。

不需要任何 Python 依赖，三个脚本都是标准库。

`dolphin-research` 是独立的 skill 目录，链接到 skills 目录即可：

```bash
ln -s ~/.workbuddy-ai/skills/trading-agents-workflow/dolphin-research ~/.workbuddy-ai/skills/dolphin-research
```

---

## 用法

**建 run 目录**（自动识别市场与基准：`.SS/.SZ`→沪深300、`.HK`→恒生、`-USD`→BTC、默认→SPY）

```bash
python scripts/init_run.py CRWD 2026-10-22
```

**定价反推**（单位：十亿美元；股价用绝对价格）

```bash
python scripts/implied.py \
  --ev 241.40 --fcf0 1.80 --r 0.10 --tg 0.03 \
  --price 239.34 --shares 1.0261 --rev-next 7.38
```

输出四块：反向 DCF 表 / 增速敏感度 / 情景价位 / 共识隐含 EPS。

**渲染报告**

```bash
python scripts/build_report.py --md runs/CRWD_2026-10-22/report.md \
  --out runs/CRWD_2026-10-22/report.html --title CRWD
```

零依赖的 markdown 子集渲染器（标题/表格/列表/引用/分隔线），输出带侧边目录、评级徽章、打印样式、响应式。A股口径红涨绿跌。

**成本档位**

| 档位 | 分析师 | 辩论轮数 | 适用 |
|---|---|---|---|
| 快 | 基本面 + 新闻 | 0（跳过辩论直接裁决） | 日常跟踪 |
| 标准 | 四个全开 | 多空 1 + 风险 1 | 默认 |
| 深挖 | 四个全开 | 多空 2 + 风险 2 | 建仓、写深度稿 |

---

## 八条硬规则

写在 `SKILL.md` 里，是这个 skill 和「让模型随便写篇研报」的分界线：

1. **一阶段一文件。** 每个角色只读上游文件、只写自己的文件，不靠对话记忆串联。
2. **对外报告是合成品，不是拼装品。** 角色原文留作审计，`report.md` 必须重写，不出现"XX 分析师认为"。
3. **数字必须有来源和日期。** 拿不到就写 `未获取`，不估算、不用记忆里的旧值填充。
4. **point-in-time。** 分析日 = 数据截止日。
5. **评级只有五档**：Buy / Overweight / Hold / Underweight / Sell。解析不出记 `REVIEW`（需人工复核），不是 Hold。
6. **辩论不许和稀泥。** 冲突本身不构成 Hold 的理由。
7. **交易员的价格锚必须是绝对价格**（189.5），不许写百分比或区间。
8. **技术面是附录。** 可以出现价格、ATR、关键位，但只能用于"怎么执行"，不能用于"为什么看好/看空"。

---

## 局限

- **不可复现。** 同一标的跑两次可能给不同评级。这不是 bug，本身是信息。
- **没有回测。** 只有决策记忆的事后结算：决策写入 `pending`，5 个交易日后按收盘结算，算绝对收益与对基准 alpha，把教训回注下一轮。
- **数据源是检索，不是 API。** 拿不到的数会缺，附录 B 会逐条列出来。
- **单模型扮演多角色**，角色隔离靠文件不靠上下文，所以硬规则 1 是必需的。
- **不构成投资建议。** 这是研究流程的工程实现，不是选股信号。

---

## 署名

本项目的角色划分、辩论轮次路由、五档评级解析、决策记忆与事后反思机制，均改编自：

> **TradingAgents** — Tauric Research
> https://github.com/TauricResearch/TradingAgents
> Apache License 2.0

报告结构、定价反推方法论、技术面降级、合成报告规则为本项目新增。修改说明见 [NOTICE](NOTICE)。

同样以 **Apache License 2.0** 发布，见 [LICENSE](LICENSE)。
