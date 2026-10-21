# 步骤 3a — Contextual Retrieval（机械拼接）实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让索引里的每一块带上「这轮对话在聊什么」，把用户提问的词汇注入到对方回复所在的块里，然后用现有 eval 量化收益。

**Architecture:** 新增 `extract_target_with_context()` —— 遍历消息，维护「最近一条非目标发言」，给每条目标消息加上 `【用户说】…\n【妈妈回复】…` 前缀。保留原来的 `extract_target_only()` 作为对照组。eval CLI 增加 `--extractor {plain,contextual}`，用同一份 golden set、同一条管线，只切换抽取方式，做 A/B 对比。

**Tech Stack:** Python 3.13 / pytest / ChromaDB / BGE-small-zh-v1.5

**Spec:** `docs/superpowers/specs/2026-10-11-agent-engineering-roadmap-design.md`（§4 步骤 3）

## 当前基线

```
语料：53,546 字 → 115 块
题目：36 条
recall@1 0.083 / recall@5 0.167 / MRR 0.109
诊断：83% 的问答对零字面重叠，索引只含对方发言
```

## Global Constraints

- **一次只改一个变量。** 本步骤只改「抽取方式」；`chunk_size=512`、`chunk_overlap=64`、embedding 模型、距离度量**全部不动**。否则无法归因。
- **评估必须用生产同一条管线。** `api/setup.py` 改用什么，eval 就该用什么。
- **保留对照组。** 不删除 `extract_target_only`，它是 A/B 的另一半。
- **evidence 稳定性。** golden set 用 evidence 文本定位；新增前缀不影响匹配，因为原回复内容仍然是索引文本的子串。
- **隐私**：真实语料与结果不入库（已有 gitignore 保证）。

## Review Focus

1. **连发多条消息** —— 目标人物连续发 3 条时，语境应一直沿用同一条用户提问，而不是丢掉。
2. **目标人物先开口** —— 没有前置用户消息时，不应拼出 `【用户说】` 空壳。
3. **超长用户消息** —— 一条 500 字的用户发言会把语境灌满很多块，必须截断（上限 120 字）。
4. **上下文导致块数增加** —— 语料变长，chunk 数会上升。这是预期内的，不是 bug；但要记录在结果里。
5. **重跑基线不可复现** —— 跑 `--extractor plain` 应能与之前的 0.167 对齐（同一 golden set、同一参数）。若不一致，说明有别的东西被改了。

---

## 文件结构

| 文件 | 改动 |
|---|---|
| `backend/rag/chunker.py` | 新增 `extract_target_with_context` |
| `backend/tests/test_chunker.py` | 新增 4 个用例 |
| `backend/evals/retrieval.py` | `build_index` 增加 `extractor` 参数 |
| `backend/evals/run.py` | 新增 `--extractor` 参数，并记入结果 |
| `backend/api/setup.py` | 改用新函数 |
| `backend/tests/test_evals.py` | 补一个 extractor 分发的用例 |

---

### Task 1: 新增 `extract_target_with_context`（含测试）

**Files:**
- Modify: `backend/rag/chunker.py`
- Modify: `backend/tests/test_chunker.py`

**Interfaces:**
- Produces: `rag.chunker.extract_target_with_context(raw_text: str, target_name: str, max_context_len: int = 120) -> str`
- 保留: `rag.chunker.extract_target_only(raw_text, target_name) -> str`（对照组）

- [ ] **Step 1: 写失败的测试**

先把文件顶部的 import 改成：

```python
from rag.chunker import (
    extract_target_only,
    extract_target_with_context,
    parse_chat_log,
)
```

然后在文件末尾追加：

```python
def test_context_carried_across_consecutive_replies():
    """连发多条时，语境沿用同一条用户提问。"""
    chat = (
        "2024-01-01 10:00 '我'\n你还记得去北京那次吗\n"
        "2024-01-01 10:01 '妈妈'\n记得啊\n"
        "2024-01-01 10:02 '妈妈'\n那天特别冷\n"
    )
    out = extract_target_with_context(chat, "妈妈")
    assert out.count("你还记得去北京那次吗") == 2


def test_new_user_message_updates_context():
    """用户再开口时，语境切换。"""
    chat = (
        "2024-01-01 10:00 '我'\n第一件事\n"
        "2024-01-01 10:01 '妈妈'\n回复一\n"
        "2024-01-01 10:02 '我'\n第二件事\n"
        "2024-01-01 10:03 '妈妈'\n回复二\n"
    )
    out = extract_target_with_context(chat, "妈妈")
    first_block, second_block = out.split("\n\n")
    assert "第一件事" in first_block and "回复一" in first_block
    assert "第二件事" in second_block and "回复二" in second_block


def test_target_speaking_first_has_no_empty_context():
    """目标人物先开口时，不该拼出空的【用户说】。"""
    chat = "2024-01-01 10:00 '妈妈'\n我先说一句\n"
    assert extract_target_with_context(chat, "妈妈") == "我先说一句"


def test_context_is_truncated():
    """超长用户消息必须截断，否则会灌满很多块。"""
    long_user = "啊" * 300
    chat = (
        f"2024-01-01 10:00 '我'\n{long_user}\n"
        "2024-01-01 10:01 '妈妈'\n回复内容\n"
    )
    out = extract_target_with_context(chat, "妈妈")
    assert "啊" * 120 in out
    assert "啊" * 121 not in out
```

- [ ] **Step 2: 跑测试，确认失败**

```powershell
cd D:\重逢2\backend
python -m pytest tests/test_chunker.py -v
```

Expected: 4 个新用例全部 FAIL，报 `ImportError: cannot import name 'extract_target_with_context'`。

- [ ] **Step 3: 实现**

在 `backend/rag/chunker.py` 末尾追加：

```python
def extract_target_with_context(
    raw_text: str,
    target_name: str,
    max_context_len: int = 120,
) -> str:
    """提取目标人物的消息，并为每条附上「最近一条用户发言」作为语境。

    聊天记录的语境就在相邻对话里，机械拼接即可拿到，不需要 LLM 生成。
    连续发多条时，语境一直沿用，直到用户再次发言。
    """
    msgs = parse_chat_log(raw_text)
    last_user = ""
    units: list[str] = []

    for msg in msgs:
        if msg["sender"] != target_name:
            last_user = msg["content"].strip()[:max_context_len]
            continue

        content = msg["content"].strip()
        if not content:
            continue

        if last_user:
            units.append(f"【用户说】{last_user}\n【{target_name}回复】{content}")
        else:
            units.append(content)

    return "\n\n".join(units)
```

- [ ] **Step 4: 跑测试，确认通过**

```powershell
python -m pytest tests/test_chunker.py -v
```

Expected: 7 passed（原有 3 + 新增 4）。

- [ ] **Step 5: 提交**

```powershell
cd D:\重逢2
git add backend/rag/chunker.py backend/tests/test_chunker.py
git status
git commit -m "feat: add contextual extraction for chat logs" -m "把最近一条用户发言拼到每条目标回复前面，让提问的词汇进入索引块。聊天记录的语境本来就在相邻对话里，机械拼接即可，无需 LLM 生成。连续回复沿用同一语境；超长提问截断到 120 字。保留原 extract_target_only 作为 A/B 对照组。"
git show --stat HEAD
```

---

### Task 2: 接入 eval 与生产

**Files:**
- Modify: `backend/evals/retrieval.py`、`backend/evals/run.py`、`backend/api/setup.py`
- Modify: `backend/tests/test_evals.py`

**Interfaces:**
- `evals.retrieval.build_index(chat_log, target_name, extractor: str = "contextual") -> tuple[int, int]`
- CLI: `--extractor {plain,contextual}`，默认 `contextual`

- [ ] **Step 1: 改 `evals/retrieval.py`**

```python
from rag.chunker import (
    chunk_text,
    extract_target_only,
    extract_target_with_context,
)

EXTRACTORS = {
    "plain": extract_target_only,
    "contextual": extract_target_with_context,
}


def build_index(
    chat_log: str,
    target_name: str,
    extractor: str = "contextual",
) -> tuple[int, int]:
    """用与生产相同的管线建索引。extractor 决定块里带不带对话语境。"""
    if extractor not in EXTRACTORS:
        raise ValueError(f"未知的 extractor: {extractor}")
    target_text = EXTRACTORS[extractor](chat_log, target_name)
    ...
```

（其余部分不变。）

- [ ] **Step 2: 改 `evals/run.py`**

新增参数：

```python
    parser.add_argument(
        "--extractor",
        choices=["plain", "contextual"],
        default="contextual",
        help="plain=只取对方发言（旧基线）；contextual=带对话语境",
    )
```

调用与记录：

```python
    target_chars, n_chunks = build_index(chat_log, args.target, extractor=args.extractor)
```

结果里加入：

```python
        "config": {
            ...
            "extractor": args.extractor,
        },
```

- [ ] **Step 3: 改 `api/setup.py`**

import 改为：

```python
from rag.chunker import chunk_text, extract_target_only, extract_target_with_context
```

调用改为：

```python
            target_text = extract_target_with_context(req.chat_log, req.name)
```

> `extract_target_only` 仍然保留在 import 里吗？**不需要** —— setup.py 只用新的那个，删掉未使用的导入。
> （但它仍被 `evals/retrieval.py` 使用，函数本身保留。）

最终 import 行：

```python
from rag.chunker import chunk_text, extract_target_with_context
```

- [ ] **Step 4: 补一个分发测试**

把 `backend/tests/test_evals.py` 顶部的 import 改成：

```python
import pytest

from evals.golden import build_golden, evidence_key
from evals.retrieval import EXTRACTORS, build_index, mrr, recall_at_k, score_all
```

然后在文件末尾追加：

```python
def test_extractors_registry_has_both():
    assert set(EXTRACTORS) == {"plain", "contextual"}


def test_unknown_extractor_raises():
    with pytest.raises(ValueError):
        build_index("", "妈妈", extractor="nope")
```

- [ ] **Step 5: 跑全部测试**

```powershell
python -m pytest -v
```

Expected: **33 passed**（27 + 4 + 2）。

- [ ] **Step 6: 提交**

```powershell
git add backend/evals/retrieval.py backend/evals/run.py backend/api/setup.py backend/tests/test_evals.py
git commit -m "feat: switch setup and eval to contextual extraction" -m "setup 改用带语境的抽取；eval 增加 --extractor 开关，可复跑旧基线做 A/B。"
git show --stat HEAD
```

---

### Task 3: A/B 测量

- [ ] **Step 1: 复跑旧基线（对照）**

```powershell
cd D:\重逢2\backend
python -m evals.run --chat-log "C:/Users/Legion/Downloads/texts/私聊_妈妈.txt" --target 妈妈 --limit 50 --extractor plain
```

Expected: `recall@5 ≈ 0.1667`，`chunks ≈ 115`。
**如果对不上，停下来查** —— 说明有别的变量被动了。

- [ ] **Step 2: 跑新方案**

```powershell
python -m evals.run --chat-log "C:/Users/Legion/Downloads/texts/私聊_妈妈.txt" --target 妈妈 --limit 50 --extractor contextual
```

- [ ] **Step 3: 记录对比**

把两次的 `metrics` 和 `corpus.chunks` 写进 ADR：

`docs/decisions/0006-contextual-retrieval.md`，包含：

- 背景（83% 零重叠的诊断）
- 方案（机械拼接 vs LLM 生成，为什么选前者）
- **A/B 数字表格**
- 块数变化及原因
- 结论：收益是否值得
- 若收益不明显，下一步该检查什么

- [ ] **Step 4: 提交 ADR**

```powershell
git add docs/decisions/0006-contextual-retrieval.md
git commit -m "docs: record contextual retrieval A/B result"
git show --stat HEAD
```

---

## 完成标准

- [ ] `python -m pytest -v` → 33 passed
- [ ] `--extractor plain` 复现旧基线（recall@5 ≈ 0.167）
- [ ] `--extractor contextual` 有新的数字，且写进 ADR
- [ ] `api/setup.py` 已切到新抽取方式
- [ ] 能口头回答：
  - 为什么选机械拼接而不是 LLM 生成？各自的代价是什么？
  - 如果 recall 提升明显，主要来自哪个机制？
  - 如果提升不明显，下一步该查什么？
