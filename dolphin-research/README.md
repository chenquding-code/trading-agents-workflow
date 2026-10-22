# dolphin-research

把海豚投研（长桥·海豚研究）2026 年的研究方法做成一个可调用的 Skill。用海豚的方法读财报、做个股深度、做行业研究时，模型按编号调出对应方法和公司卡片，照着做。

来源是海豚投研 2026-01-01 至 2026-10-19 的全部中文原文（英文版为机翻，未使用）：分析长文 367 篇，火线速读与短评 284 条。逐篇通读后抽出 3419 条方法，每条都带原文案例和数字。电话会纪要 265 篇只列在清单里，没有纳入提炼。

| 框架 | 定位 | 规模 | 附录A |
|---|---|---|---|
| 财报 | 追踪公司的边际变化：财报前预期 → 速读定性 → 口径清洗 → 收入、利润、指引、现金流拆解 → 股价归因 → 估值更新 → 分行业指标体系 | 17 章 · 108 节 · 1287 法 | 106 家公司的财报追踪卡 |
| 个股 | 个股深度：立项与预期差 → 成长史 → 商业模式与单位经济 → 空间与护城河 → 财务预测 → 估值 → 治理与特殊情境 → 风险与结论 | 15 章 · 78 节 · 992 法 | 88 张公司研究卡 |
| 行业 | 行业与赛道：产业链与价值分配 → 需求、供给、价格周期 → 技术路线 → 空间与渗透率 → 竞争 → 商业模式与入口 → 政策地缘 → 标的映射 → 宏观数据与策略 | 17 章 · 78 节 · 702 法 | 86 张行业/赛道卡 |

---

## 为什么要一个检索脚本

正文一共约 8 MB，单个章节文件 50–500 KB，整份读进上下文既慢又会挤掉别的东西。所以 `SKILL.md` 只放路由、精简版流程和硬规则，正文全部通过 `scripts/dolphin.py` 按编号取：

```bash
python3 scripts/dolphin.py card CoreWeave            # 三套框架里的 CoreWeave 卡片
python3 scripts/dolphin.py overview 财报 SOP         # 财报研究的标准作业流程
python3 scripts/dolphin.py toc 个股 10               # 第 10 章目录
python3 scripts/dolphin.py show 个股 10.1 --brief    # 一节的方法要点 + 速查清单
python3 scripts/dolphin.py show 财报 9.2.2           # 单个方法全文
python3 scripts/dolphin.py search 隐含 Q4            # 关键词找方法
python3 scripts/dolphin.py checklist 财报 9.2        # 本节速查清单
python3 scripts/dolphin.py source 台积电             # 海豚原文出处与链接
```

只用标准库，Python 3.7 以上就能跑。

---

## 安装

**Claude Code**

```bash
git clone https://github.com/chenquding-code/trading-agents-workflow.git ~/src/trading-agents-workflow
ln -s ~/src/trading-agents-workflow/dolphin-research ~/.claude/skills/dolphin-research
```

**WorkBuddy**

```bash
ln -s ~/.workbuddy-ai/skills/trading-agents-workflow/dolphin-research ~/.workbuddy-ai/skills/dolphin-research
```

装好之后，在对话里说「用海豚的方法看一下 NVDA 这季财报」「按海豚的框架给 CoreWeave 做个财报前预期表」「海豚是怎么给周期股估值的」，就会触发。

---

## 一次调用大概是什么样

以「用海豚的方法做美光下季财报的前瞻」为例：

1. **选框架**：财报前瞻，主框架是`财报`第 1 章
2. **查卡片**：`card 美光`，拿到海豚每季盯的核心问题、必看指标清单、预期基准和估值方法
3. **走流程**：`overview 财报 SOP` 阶段 A。搭多层预期基准（1.1），锁定核心指标（1.3），还原买方预期（1.2），确认估值水位（11.3）
4. **行业指标**：`overview 财报 按行业查指标` → 15.1 半导体与设备 → `show 财报 15.1 --brief`
5. **取方法照做**：`show 财报 1.1.4` 等，按「操作步骤」用最新数据算，按「判断标准」解读读数
6. **查漏**：`checklist 财报 1.1`
7. **成文**：按 `overview 财报 追踪表` 的模板填预期表

---

## 目录

```
dolphin-research/
├── SKILL.md                      路由、精简流程、核心判断习惯、硬规则
├── scripts/dolphin.py            检索工具
└── references/
    ├── 财报/  00_总览 + 17 章正文 + 附录A 公司财报追踪卡片库 + 附录_文章清单
    ├── 个股/  00_总览 + 15 章正文 + 附录A 个股研究卡片库 + 附录_文章清单
    └── 行业/  00_总览 + 17 章正文 + 附录A 行业研究卡片库 + 附录_文章清单
```

每个 `00_总览与使用指南.md` 都包括：章节地图（每节回答什么问题）、19–20 条核心心法、标准流程、立项问卷或清单、按公司/行业类型选方法、如何衍生新方法。

---

## 局限

- **时间窗口**：只覆盖 2026-01-01 至 2026-10-19。卡片记录的是那时的状态，案例数字和阈值也是原文当时的口径，用到新公司或新时期要重新校准。
- **是方法，不是结论**：框架不含对任何公司的投资建议。
- **不含原文全文**：仓库只放提炼后的方法和卡片，原文链接见各框架的 `附录_文章清单.md`。本地有原文时，放到 `references/<框架>/原文/`（已在 `.gitignore` 里排除），或者用环境变量 `DOLPHIN_SOURCES` 指向它。

## 内容来源

方法、案例与卡片提炼自 [海豚投研](https://longbridge.com/zh-CN/dolphin)（长桥·海豚研究）公开发布的中文文章。文中引用的文章标题、数据与观点归原作者所有。
