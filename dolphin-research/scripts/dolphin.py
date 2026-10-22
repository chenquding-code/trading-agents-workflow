#!/usr/bin/env python3
"""海豚投研方法论检索工具。只用标准库，Python 3.7+。

正文文件单个 50–500 KB，不要整份读进上下文。用这个脚本按编号取段落、按关键词找方法、调卡片。

用法：
  dolphin.py toc [框架] [章|节]           目录。不带框架列三套框架的章；带 9 列第 9 章的节与方法；带 9.2 列该节方法
  dolphin.py show <框架> <编号> [--brief]  正文。9.2.3 = 单个方法；9.2 = 整节（--brief 只给方法要点 + 速查清单）；9 = 章导读
  dolphin.py checklist <框架> <节>         该节末尾的「本节速查清单」
  dolphin.py search <关键词...> [-f 框架] [--titles] [-n 30]
                                          多关键词取交集；标题命中排在前面，再列正文命中
  dolphin.py card <关键词> [-f 框架] [--list] [--all]
                                          附录A 卡片：命中 ≤3 张直接打印全文，更多则列清单
  dolphin.py overview <框架> [部分]        00_总览：不带参数列出各部分；部分可写 一~六 / 1~6 / 标题关键词（如 SOP、心法）
  dolphin.py source <关键词> [-f 框架]     来源文章：日期、类型、标题、链接；本地有原文时给出路径

框架：财报 | 个股 | 行业，也接受 earnings / stock / industry 或 e / s / i。
原文目录：默认找 references/<框架>/原文/；也可以设环境变量 DOLPHIN_SOURCES，指向含 财报/个股/行业 子目录的文件夹
（<dir>/财报/原文/ 或 <dir>/财报/ 两种摆法都认）。
"""

import argparse
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "references"
FRAMEWORKS = ["财报", "个股", "行业"]
ALIASES = {
    "财报": "财报", "earnings": "财报", "e": "财报",
    "个股": "个股", "stock": "个股", "s": "个股",
    "行业": "行业", "industry": "行业", "i": "行业",
}
CN_NUM = "一二三四五六七八九十"

RE_CHAPTER = re.compile(r"^# 第(\d+)章\s+(.*)$")
RE_SECTION = re.compile(r"^## (\d+\.\d+)\s+(.*)$")
RE_METHOD = re.compile(r"^### (\d+\.\d+\.\d+)\s+(.*)$")
CHECKLIST_MARK = "**本节速查清单**"


def fw_of(name):
    key = (name or "").strip().lower()
    if key not in ALIASES:
        sys.exit("未知框架：%s（可选：财报 / 个股 / 行业）" % name)
    return ALIASES[key]


def read_lines(path):
    return path.read_text(encoding="utf-8").splitlines()


def chapter_files(fw):
    files = [p for p in (ROOT / fw).glob("[0-9][0-9]_*.md") if not p.name.startswith("00_")]
    return sorted(files, key=lambda p: int(p.name[:2]))


def one_file(fw, pattern):
    hits = sorted((ROOT / fw).glob(pattern))
    if not hits:
        sys.exit("找不到 %s/%s" % (fw, pattern))
    return hits[0]


# ---------- 正文索引 ----------

class Node(object):
    __slots__ = ("fw", "id", "level", "title", "path", "lines", "start", "end")

    def __init__(self, fw, id_, level, title, path, lines, start):
        self.fw, self.id, self.level, self.title = fw, id_, level, title
        self.path, self.lines, self.start, self.end = path, lines, start, len(lines)

    def body(self):
        seg = self.lines[self.start:self.end]
        if self.level == 3:  # 一节最后一个方法后面跟着速查清单，不算方法正文
            for i, line in enumerate(seg):
                if line.strip() == CHECKLIST_MARK:
                    seg = seg[:i]
                    break
        while seg and seg[-1].strip() in ("", "---"):
            seg = seg[:-1]
        return seg

    def loc(self):
        return "%s/%s:%d" % (self.fw, self.path.name, self.start + 1)


_INDEX = {}


def index(fw):
    if fw in _INDEX:
        return _INDEX[fw]
    nodes = []
    for path in chapter_files(fw):
        lines = read_lines(path)
        file_nodes = []
        for i, line in enumerate(lines):
            for level, rx in ((1, RE_CHAPTER), (2, RE_SECTION), (3, RE_METHOD)):
                m = rx.match(line)
                if m:
                    file_nodes.append(Node(fw, m.group(1), level, m.group(2).strip(), path, lines, i))
                    break
        for k, node in enumerate(file_nodes):
            for later in file_nodes[k + 1:]:
                if later.level <= node.level:
                    node.end = later.start
                    break
        nodes.extend(file_nodes)
    _INDEX[fw] = nodes
    return nodes


def find_node(fw, id_):
    id_ = id_.strip().rstrip(".")
    for n in index(fw):
        if n.id == id_:
            return n
    sys.exit("%s 里没有编号 %s。先用 toc 看目录。" % (fw, id_))


def children(fw, parent):
    prefix = parent.id + "."
    return [n for n in index(fw) if n.level == parent.level + 1 and n.id.startswith(prefix)]


def method_gist(node):
    """方法要点那一行（去掉字段名）。"""
    for line in node.body():
        s = line.strip()
        if s.startswith("- **方法要点**"):
            return re.sub(r"^- \*\*方法要点\*\*[：:]\s*", "", s)
    return ""


def checklist_lines(section):
    seg = section.lines[section.start:section.end]
    for i, line in enumerate(seg):
        if line.strip() == CHECKLIST_MARK:
            out = seg[i:]
            while out and out[-1].strip() in ("", "---"):
                out = out[:-1]
            return out
    return []


# ---------- 命令 ----------

def cmd_toc(a):
    if not a.fw:
        for fw in FRAMEWORKS:
            nodes = index(fw)
            n_sec = sum(1 for n in nodes if n.level == 2)
            n_met = sum(1 for n in nodes if n.level == 3)
            print("## %s（%d 节 · %d 个方法）" % (fw, n_sec, n_met))
            for n in nodes:
                if n.level == 1:
                    print("  第%s章 %s" % (n.id, n.title))
            print()
        return
    fw = fw_of(a.fw)
    nodes = index(fw)
    if not a.id:
        for n in nodes:
            if n.level == 1:
                print("第%s章 %s  [%s]" % (n.id, n.title, n.path.name))
            elif n.level == 2:
                print("  %s %s（%d）" % (n.id, n.title, len(children(fw, n))))
        return
    root = find_node(fw, a.id)
    print("%s %s  [%s]" % (root.id, root.title, root.loc()))
    for c in children(fw, root):
        print("  %s %s" % (c.id, c.title))
        if root.level == 1:
            for g in children(fw, c):
                print("    %s %s" % (g.id, g.title))


def cmd_show(a):
    fw = fw_of(a.fw)
    node = find_node(fw, a.id)
    print("<!-- %s -->" % node.loc())
    if node.level == 1:
        # 章：只给章导读和本章小节，正文太长
        body = node.body()
        for i, line in enumerate(body):
            if RE_SECTION.match(line):
                body = body[:i]
                break
        print("\n".join(body).rstrip())
        print()
        for c in children(fw, node):
            print("- %s %s（%d 个方法）" % (c.id, c.title, len(children(fw, c))))
        print("\n（章正文太长，按节读：show %s <节号> [--brief]）" % fw)
        return
    if node.level == 2 and a.brief:
        body = node.body()
        print(body[0])
        for line in body[1:]:
            if line.startswith("> "):
                print(line)
                break
        print()
        for c in children(fw, node):
            print("### %s %s" % (c.id, c.title))
            gist = method_gist(c)
            if gist:
                print(gist)
            print()
        print("\n".join(checklist_lines(node)))
        return
    print("\n".join(node.body()))


def cmd_checklist(a):
    fw = fw_of(a.fw)
    node = find_node(fw, a.id)
    if node.level != 2:
        sys.exit("速查清单按节给，请传节号（如 9.2）。")
    out = checklist_lines(node)
    print("## %s %s\n" % (node.id, node.title))
    print("\n".join(out) if out else "（本节没有速查清单）")


def cmd_search(a):
    terms = [t.lower() for t in a.terms]
    fws = [fw_of(a.fw)] if a.fw else FRAMEWORKS
    title_hits, body_hits = [], []
    for fw in fws:
        for n in index(fw):
            if n.level == 1:
                continue
            title = n.title.lower()
            if all(t in title for t in terms):
                title_hits.append(n)
            elif not a.titles and n.level == 3:
                text = "\n".join(n.body()).lower()
                if all(t in text for t in terms):
                    body_hits.append((sum(text.count(t) for t in terms), n, text))
    body_hits.sort(key=lambda x: -x[0])
    shown = 0
    if title_hits:
        print("## 标题命中（%d）" % len(title_hits))
        for n in title_hits[:a.n]:
            kind = "节" if n.level == 2 else "法"
            print("%s %-9s [%s] %s  — %s" % (n.fw, n.id, kind, n.title, n.loc()))
            shown += 1
    if body_hits and shown < a.n:
        print("\n## 正文命中（%d，按命中次数排序）" % len(body_hits))
        for _, n, text in body_hits[:a.n - shown]:
            # 摘录跳过标题行，落在最少见的那个词第一次出现的位置
            raw = "\n".join(n.body()[1:])
            low = raw.lower()
            rare = min(terms, key=lambda t: low.count(t) or 10 ** 9)
            pos = max(low.find(rare), 0)
            snippet = raw[max(0, pos - 30):pos + 50].replace("\n", " ")
            print("%s %-9s %s\n    …%s…" % (n.fw, n.id, n.title, snippet))
    if not title_hits and not body_hits:
        print("没有命中。换个说法，或少放几个关键词。")
    cards = [(fw, h) for fw in fws for h, _, _ in parse_cards(fw) if all(t in h.lower() for t in terms)]
    if cards:
        print("\n## 相关卡片（card 命令可直接打开）")
        for fw, h in cards:
            print("%s  %s" % (fw, h))


def parse_cards(fw):
    path = one_file(fw, "附录A_*.md")
    lines = read_lines(path)
    starts = [i for i, l in enumerate(lines) if l.startswith("### ")]
    cards = []
    for k, s in enumerate(starts):
        e = starts[k + 1] if k + 1 < len(starts) else len(lines)
        for j in range(s + 1, e):
            if lines[j].startswith("## ") or lines[j].startswith("# "):
                e = j
                break
        seg = lines[s:e]
        while seg and seg[-1].strip() in ("", "---"):
            seg = seg[:-1]
        cards.append((lines[s][4:].strip(), seg, "%s/%s:%d" % (fw, path.name, s + 1)))
    return cards


def cmd_card(a):
    fws = [fw_of(a.fw)] if a.fw else FRAMEWORKS
    if a.list:
        for fw in fws:
            cards = parse_cards(fw)
            print("## %s（%d 张）" % (fw, len(cards)))
            for h, _, _ in cards:
                if not a.keyword or a.keyword.lower() in h.lower():
                    print("- " + h)
            print()
        return
    if not a.keyword:
        sys.exit("要给关键词（公司名、代码或行业名），或用 --list 列全部卡片。")
    kw = a.keyword.lower()
    hits, mentions = [], []
    for fw in fws:
        for h, seg, loc in parse_cards(fw):
            if kw in h.lower():
                hits.append((fw, h, seg, loc))
            elif kw in "\n".join(seg).lower():
                mentions.append((fw, h, loc))
    if hits and (len(hits) <= 3 or a.all):
        for fw, h, seg, loc in hits:
            print("<!-- %s · %s -->" % (fw, loc))
            print("\n".join(seg))
            print()
    elif hits:
        print("命中 %d 张卡片，缩小关键词或加 --all：" % len(hits))
        for fw, h, _, loc in hits:
            print("%s  %s  [%s]" % (fw, h, loc))
    else:
        print("没有以「%s」为标题的卡片。" % a.keyword)
    if mentions and (not hits or a.all):
        print("\n正文提到「%s」的卡片：" % a.keyword)
        for fw, h, loc in mentions[:20]:
            print("%s  %s  [%s]" % (fw, h, loc))


def cmd_overview(a):
    fw = fw_of(a.fw)
    path = one_file(fw, "00_*.md")
    lines = read_lines(path)
    heads = []
    for i, l in enumerate(lines):
        m = re.match(r"^(#{2,4}) (.*)$", l)
        if m:
            heads.append((i, len(m.group(1)), m.group(2).strip()))
    if not a.part:
        print("%s/%s\n" % (fw, path.name))
        for i, lv, t in heads:
            if lv == 2:
                print(t)
            elif lv == 3:
                print("    " + t)
        return
    part = " ".join(a.part).strip()
    if part.isdigit() and 1 <= int(part) <= 10:
        part = CN_NUM[int(part) - 1]
    target = None
    for k, (i, lv, t) in enumerate(heads):
        if lv == 2 and t.startswith(part + "、"):
            target = k
            break
    if target is None:
        for k, (i, lv, t) in enumerate(heads):
            if part.lower() in t.lower():
                target = k
                break
    if target is None:
        sys.exit("00_总览里没有「%s」。不带参数运行可看各部分标题。" % part)
    i0, lv0, _ = heads[target]
    i1 = len(lines)
    for i, lv, _ in heads[target + 1:]:
        if lv <= lv0:
            i1 = i
            break
    seg = lines[i0:i1]
    while seg and seg[-1].strip() in ("", "---"):
        seg = seg[:-1]
    print("<!-- %s/%s:%d -->" % (fw, path.name, i0 + 1))
    print("\n".join(seg))


def source_dirs(fw):
    dirs = [ROOT / fw / "原文"]
    env = os.environ.get("DOLPHIN_SOURCES")
    if env:
        base = Path(env).expanduser() / fw
        dirs[:0] = [base / "原文", base]  # 两种摆法都认：<dir>/财报/原文/ 或 <dir>/财报/
    return [d for d in dirs if d.is_dir()]


def cmd_source(a):
    fws = [fw_of(a.fw)] if a.fw else FRAMEWORKS
    kw = a.keyword.lower()
    seen = set()
    n = 0
    for fw in fws:
        path = one_file(fw, "附录_文章清单.md")
        dirs = source_dirs(fw)
        for line in read_lines(path):
            if not line.startswith("| 20") or kw not in line.lower():
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) < 4:
                continue
            m = re.search(r"\[(.*)\]\((https?://[^)]+)\)", cells[3])
            title, url = (m.group(1), m.group(2)) if m else (cells[3], "")
            if url in seen:
                continue
            seen.add(url)
            print("%s  %s  %s  《%s》\n    %s" % (cells[0], cells[1], cells[2], title, url))
            pid = url.rstrip("/").rsplit("/", 1)[-1]
            for d in dirs:
                local = sorted(d.glob("*_%s.md" % pid))
                if local:
                    print("    本地原文：%s" % local[0])
                    break
            n += 1
            if n >= a.n:
                print("\n（只列前 %d 条，用 -n 调整）" % a.n)
                return
    if not n:
        print("文章清单里没有「%s」。" % a.keyword)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="海豚投研方法论检索", formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd")

    s = sub.add_parser("toc", help="目录")
    s.add_argument("fw", nargs="?")
    s.add_argument("id", nargs="?")
    s.set_defaults(func=cmd_toc)

    s = sub.add_parser("show", help="按编号取正文")
    s.add_argument("fw")
    s.add_argument("id")
    s.add_argument("--brief", action="store_true", help="整节时只给方法要点与速查清单")
    s.set_defaults(func=cmd_show)

    s = sub.add_parser("checklist", help="本节速查清单")
    s.add_argument("fw")
    s.add_argument("id")
    s.set_defaults(func=cmd_checklist)

    s = sub.add_parser("search", help="关键词找方法")
    s.add_argument("terms", nargs="+")
    s.add_argument("-f", "--fw")
    s.add_argument("--titles", action="store_true", help="只搜标题")
    s.add_argument("-n", type=int, default=30)
    s.set_defaults(func=cmd_search)

    s = sub.add_parser("card", help="附录A 卡片")
    s.add_argument("keyword", nargs="?")
    s.add_argument("-f", "--fw")
    s.add_argument("--list", action="store_true")
    s.add_argument("--all", action="store_true")
    s.set_defaults(func=cmd_card)

    s = sub.add_parser("overview", help="00_总览各部分")
    s.add_argument("fw")
    s.add_argument("part", nargs="*")
    s.set_defaults(func=cmd_overview)

    s = sub.add_parser("source", help="来源文章")
    s.add_argument("keyword")
    s.add_argument("-f", "--fw")
    s.add_argument("-n", type=int, default=30)
    s.set_defaults(func=cmd_source)

    a = p.parse_args()
    if not a.cmd:
        print(__doc__)
        return
    a.func(a)


if __name__ == "__main__":
    main()
