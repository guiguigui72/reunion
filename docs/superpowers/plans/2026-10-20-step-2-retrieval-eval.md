# 步骤 2 — 检索评估 Harness 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为「重逢」的检索层建立可复现的评估基线 —— 给定真实问题，量化「包含答案的聊天片段」能否被检索到，产出 `recall@k` / `MRR` 并落盘。

**Architecture:** 三块纯逻辑 + 一个 CLI。`golden.py` 从真实聊天记录里配对「用户的提问 + 妈妈的第一条实质回复」，产出 evidence-based 的 golden set；`retrieval.py` 用与生产完全相同的管线（`extract_target_only` → `chunk_text` → `embed_texts` → ChromaDB）建临时索引并计算指标；`run.py` 编排并在临时 `REUNION_HOME` 下运行，结果写入 `results/`。

**Tech Stack:** Python 3.13 / pytest / ChromaDB / sentence-transformers (BGE-small-zh-v1.5)

**Spec:** `docs/superpowers/specs/2026-10-11-agent-engineering-roadmap-design.md`（§4 步骤 2）

## 本计划的范围

路线图的步骤 2 包含两块：**检索质量**与**人格/幻觉（LLM-as-judge）**。
本计划只做**第一块**——检索质量，因为它是客观、零 API 成本、且为步骤 3 提供基线的部分。

人格/幻觉评估另出一份计划，待检索基线稳定后再做。

## Global Constraints

- **隐私**：真实聊天语料与其衍生的 golden set **不得进入 git**。仓库只提交代码、合成示例和数字。
- **可复现**：评估必须使用与生产**完全相同**的检索管线，否则数字没有意义。
- **稳定性**：golden item 用 evidence 文本定位，不用 chunk id —— 必须能扛住步骤 3 的分块变更。
- **落盘**：每次评估产出一个带时间戳的 JSON（§5.4）。
- **不新增运行时依赖**：只用 `requirements.txt` 已有 + pytest。
- **不动生产代码**：本步骤只新增 `evals/`、`golden/`、`results/`、测试；`rag/` 与 `agent/` 一律不改。
  （例外：若发现必须的参数化，先记录再讨论。）

## Review Focus

1. **evidence 跨 chunk 边界** —— 若答案被切在两块之间，`evidence in doc` 会漏判。
   缓解：用 evidence 的前 40 字作为匹配键，并约束 `chunk_overlap >= 40`。
2. **重复 evidence** —— 同一句回复被多条提问引用时，指标会重复计权。按 evidence 去重。
3. **问题筛选的假阳性** —— 「吗」出现在非疑问句里（如「好吗好的」）。抽样人工检查。
4. **临时目录残留** —— 每次 CLI 运行创建临时 `REUNION_HOME`，不复用生产索引。
5. **合成示例被误当作真实基线** —— `example_golden.jsonl` 必须显式标注 synthetic，且 README 不得引用它的数字。

---

## 文件结构

| 文件 | 职责 | 提交 |
|---|---|---|
| `backend/evals/__init__.py` | 包标记 | ✅ |
| `backend/evals/golden.py` | 从聊天记录构建 golden set | ✅ |
| `backend/evals/retrieval.py` | 建索引、检索、计算指标 | ✅ |
| `backend/evals/run.py` | CLI 入口、结果落盘 | ✅ |
| `backend/tests/test_evals.py` | 纯逻辑单元测试 | ✅ |
| `backend/golden/example_golden.jsonl` | 合成示例 | ✅ |
| `backend/golden/real_golden.jsonl` | 真实数据（本地生成） | ❌ gitignore |
| `backend/results/*.json` | 评估结果 | ❌ gitignore |
| `.gitignore` | 追加两条 | ✅ |

---

### Task 1: golden 构建 + 指标纯函数（含测试）

**Files:**
- Create: `backend/evals/__init__.py`、`backend/evals/golden.py`、`backend/evals/retrieval.py`、`backend/tests/test_evals.py`
- Modify: `.gitignore`

**Interfaces:**
- Produces:
  - `evals.golden.build_golden(chat_log: str, target_name: str, min_answer_len: int = 8, limit: int | None = None) -> list[dict]`
    每项形如 `{"id": "q001", "question": str, "evidence": str}`
  - `evals.golden.evidence_key(evidence: str, n: int = 40) -> str`
  - `evals.retrieval.recall_at_k(retrieved: list[str], evidence: str, k: int) -> bool`
  - `evals.retrieval.mrr(retrieved: list[str], evidence: str) -> float`
  - `evals.retrieval.score_all(items: list[dict], retrieved_map: dict[str, list[str]], ks: tuple[int, ...] = (1, 5)) -> dict`

- [ ] **Step 1: 建目录与包标记**

`backend/evals/__init__.py`（空文件）。

`.gitignore` 追加：

```
backend/golden/real_golden.jsonl
backend/results/
```

- [ ] **Step 2: 写 golden.py**

```python
"""从真实聊天记录构建检索评估集。

设计要点：
- 用真实提问，不用合成问题（避免分布偏移）
- 用 evidence 文本定位，不用 chunk id（扛得住重新分块）
- 按 evidence 去重（同一句话被多次引用时只算一次）
"""
from __future__ import annotations

from rag.chunker import parse_chat_log

# 强标记：本身就表示「在问一件具体的事」
STRONG_MARKERS = (
    "什么", "哪", "谁", "几", "多少", "怎么", "为什么",
    "记不记得", "还记得", "有没有", "那次", "什么时候",
)

# 弱标记：可能只是语气词
WEAK_MARKERS = ("吗", "呢", "？", "?")


def looks_like_question(text: str, min_len: int = 8) -> bool:
    """强标记够 4 个字就收；弱标记必须够长。

    否则"是吗？"这类对白里的附会混进评估集，测的就不是检索能力了。
    （第一版没有这道门槛，40 条里有 31 条不到 8 个字，基线被严重虚高。）
    """
    t = text.strip()
    if len(t) < 4:
        return False
    if any(m in t for m in STRONG_MARKERS):
        return True
    return len(t) >= min_len and any(m in t for m in WEAK_MARKERS)


def evidence_key(evidence: str, n: int = 40) -> str:
    """取 evidence 的前 n 个字符作为匹配键。

    约束：生产分块的 chunk_overlap 必须 >= n，否则匹配键可能跨块被切断。
    当前 chunk_overlap = 64，n = 40，安全。
    """
    return evidence.strip()[:n]


def build_golden(
    chat_log: str,
    target_name: str,
    min_question_len: int = 8,
    min_answer_len: int = 8,
    limit: int | None = None,
) -> list[dict]:
    """扫描聊天记录，配对「用户的提问」与「目标人物的第一条实质回复」。

    跳过：
    - 目标人物自己的消息
    - 回复过短（"嗯"、"哈哈"）——它们不承载可检索的信息
    - evidence 重复的配对
    """
    msgs = parse_chat_log(chat_log)
    items: list[dict] = []
    seen_evidence: set[str] = set()

    for i, m in enumerate(msgs):
        if m["sender"] == target_name:
            continue
        question = m["content"].strip()
        if not question or not looks_like_question(question, min_len=min_question_len):
            continue

        # 往后最多看 3 条，找目标人物的第一条实质回复
        for j in range(i + 1, min(i + 4, len(msgs))):
            reply = msgs[j]
            if reply["sender"] != target_name:
                continue
            evidence = reply["content"].strip()
            if len(evidence) < min_answer_len:
                break
            key = evidence_key(evidence)
            if key in seen_evidence:
                break
            seen_evidence.add(key)
            items.append({
                "id": f"q{len(items) + 1:03d}",
                "question": question[:200],
                "evidence": evidence[:500],
            })
            break
        if limit is not None and len(items) >= limit:
            break

    return items
```

- [ ] **Step 3: 写 retrieval.py**

```python
"""检索评估：建索引、跑查询、算指标。"""
from __future__ import annotations

from evals.golden import evidence_key
from rag.chunker import chunk_text, extract_target_only
from rag.embedder import embed_texts
from rag.store import reset_collection


def recall_at_k(retrieved: list[str], evidence: str, k: int) -> bool:
    key = evidence_key(evidence)
    return any(key in doc for doc in retrieved[:k])


def mrr(retrieved: list[str], evidence: str) -> float:
    key = evidence_key(evidence)
    for rank, doc in enumerate(retrieved, start=1):
        if key in doc:
            return 1.0 / rank
    return 0.0


def build_index(chat_log: str, target_name: str) -> tuple[int, int]:
    """用生产管线建索引，返回 (消息字符数, chunk 数)。"""
    target_text = extract_target_only(chat_log, target_name)
    chunks = chunk_text(target_text)
    embeddings = embed_texts(chunks)
    collection = reset_collection("memories")
    collection.add(
        documents=chunks,
        embeddings=embeddings,
        ids=[f"mem_{i}" for i in range(len(chunks))],
    )
    return len(target_text), len(chunks)


def retrieve(question: str, n_results: int = 5) -> list[str]:
    from rag.store import query_collection
    return query_collection(embed_texts([question])[0], n_results=n_results)


def score_all(items, retrieved_map, ks=(1, 5)) -> dict:
    metrics = {f"recall@{k}": 0.0 for k in ks}
    metrics["mrr"] = 0.0
    if not items:
        return metrics

    for item in items:
        docs = retrieved_map.get(item["id"], [])
        for k in ks:
            if recall_at_k(docs, item["evidence"], k):
                metrics[f"recall@{k}"] += 1.0
        metrics["mrr"] += mrr(docs, item["evidence"])

    for key in metrics:
        metrics[key] = round(metrics[key] / len(items), 4)
    return metrics
```

- [ ] **Step 4: 写单元测试**

`backend/tests/test_evals.py`：

```python
from evals.golden import build_golden, evidence_key
from evals.retrieval import mrr, recall_at_k, score_all

CHAT = (
    "2024-01-01 10:00 '我'\n你还记得我们去北京那次吗\n"
    "2024-01-01 10:01 '妈妈'\n记得啊，那天特别冷，你非要吃冰淇淋\n"
    "2024-01-01 10:02 '我'\n哈哈是啊\n"
    "2024-01-01 10:03 '我'\n球球最近怎么样？\n"
    "2024-01-01 10:04 '妈妈'\n嗯\n"
)


def test_build_golden_pairs_question_with_reply():
    items = build_golden(CHAT, "妈妈")
    assert len(items) == 1
    assert "北京" in items[0]["question"]
    assert "冰淇淋" in items[0]["evidence"]


def test_build_golden_skips_short_replies():
    """"嗯"太短，不承载可检索信息，应被跳过。"""
    items = build_golden(CHAT, "妈妈")
    assert all(len(i["evidence"]) >= 8 for i in items)


def test_build_golden_dedupes_same_evidence():
    """同一句回复被多条提问引用时，只保留一条。"""
    chat = (
        "2024-01-01 10:00 '我'\n你还记得吗\n"
        "2024-01-01 10:01 '妈妈'\n记得啊，那天特别冷\n"
        "2024-01-01 10:02 '我'\n是吗？\n"
        "2024-01-01 10:07 '我'\n那你还记得吗\n"
        "2024-01-01 10:08 '妈妈'\n记得啊，那天特别冷\n"
    )
    assert len(build_golden(chat, "妈妈")) == 1


def test_evidence_key_is_prefix():
    assert evidence_key("一二三四五", n=3) == "一二三"


def test_recall_at_k_hit_and_miss():
    """真实的 chunk 很长（约 512 字），证据是嵌在里面的一个片段。"""
    evidence = "记得啊，那天特别冷，你非要吃冰淇淋"
    docs = [
        "完全无关的一段内容，讲的是别的事情。",
        "前面还有一些闲聊的内容。" + evidence + "后面继续聊了别的话题。",
    ]
    assert recall_at_k(docs, evidence, 2) is True
    assert recall_at_k(docs, evidence, 1) is False


def test_mrr_ranks():
    assert mrr(["a", "b"], "zzz") == 0.0
    assert mrr(["a", "b"], "b") == 0.5
    assert mrr(["b"], "b") == 1.0


def test_score_all_aggregates():
    items = [{"id": "q1", "evidence": "答案一"}, {"id": "q2", "evidence": "答案二"}]
    retrieved = {"q1": ["答案一"], "q2": ["无关"]}
    metrics = score_all(items, retrieved)
    assert metrics["recall@1"] == 0.5
    assert metrics["recall@5"] == 0.5
    assert metrics["mrr"] == 0.5
```

- [ ] **Step 5: 跑测试**

```powershell
cd backend
python -m pytest tests/test_evals.py -v
```

Expected: 9 passed。

- [ ] **Step 6: 提交**

```powershell
git add backend/evals/ backend/tests/test_evals.py .gitignore
git status
git commit -m "feat: add golden set builder and retrieval metrics" -m "golden 用真实提问 + 目标人物的实质回复配对，以 evidence 文本而非 chunk id 定位，扛得住重新分块。指标实现为纯函数，便于单测。真实 golden set 与结果文件加入 gitignore，不入库。"
git show --stat HEAD
```

（提交前先 `git status` 确认没有 `real_golden.jsonl` 或 `results/`。）

---

### Task 2: CLI 与真实基线

**Files:**
- Create: `backend/evals/run.py`、`backend/golden/example_golden.jsonl`

- [ ] **Step 1: 写 run.py**

关键点：**在 import 任何项目模块之前**把 `REUNION_HOME` 指到临时目录，确保评估不碰真实索引、也不被旧索引污染。

```python
"""检索评估 CLI。

用法：
  python -m evals.run --chat-log "C:\\path\\to\\chat.txt" --target 妈妈 --limit 40
  python -m evals.run --golden golden/real_golden.jsonl
"""
from __future__ import annotations

import os
import tempfile

# 必须在导入项目模块之前设置 —— config.py 在模块级读取它
os.environ.setdefault("REUNION_HOME", tempfile.mkdtemp(prefix="reunion-eval-"))

import argparse
import json
import time
from pathlib import Path

from evals.golden import build_golden
from evals.retrieval import build_index, retrieve, score_all

RESULTS_DIR = Path(__file__).parent.parent / "results"
GOLDEN_DIR = Path(__file__).parent.parent / "golden"


def load_chat(path: str) -> str:
    raw = Path(path).read_bytes()
    for enc in ("utf-8-sig", "utf-8", "utf-16", "gbk"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    raise RuntimeError(f"无法识别编码: {path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chat-log", help="聊天记录路径；给了就重新生成 golden set")
    parser.add_argument("--target", default="妈妈")
    parser.add_argument("--limit", type=int, default=40)
    parser.add_argument("--golden", help="复用已有的 golden jsonl")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    if args.golden:
        items = [json.loads(line) for line in Path(args.golden).read_text(encoding="utf-8").splitlines() if line.strip()]
        chat_log = None
    else:
        if not args.chat_log:
            parser.error("需要 --chat-log 或 --golden 之一")
        chat_log = load_chat(args.chat_log)
        items = build_golden(chat_log, args.target, limit=args.limit)
        GOLDEN_DIR.mkdir(exist_ok=True)
        out = GOLDEN_DIR / "real_golden.jsonl"
        out.write_text(
            "\n".join(json.dumps(i, ensure_ascii=False) for i in items) + "\n",
            encoding="utf-8",
        )
        print(f"golden set 已写入 {out}（{len(items)} 条）")

    if not items:
        print("没有构建出任何 golden item —— 检查 --target 是否与导出里的标签一致")
        return

    target_text, n_chunks = build_index(chat_log, args.target) if chat_log else (0, 0)

    retrieved_map = {i["id"]: retrieve(i["question"], n_results=args.top_k) for i in items}
    metrics = score_all(items, retrieved_map)

    result = {
        "time": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "corpus": {"target_chars": target_text, "chunks": n_chunks},
        "golden": {"items": len(items)},
        "metrics": metrics,
        "config": {"model": "BAAI/bge-small-zh-v1.5", "space": "cosine", "top_k": args.top_k},
    }

    RESULTS_DIR.mkdir(exist_ok=True)
    out = RESULTS_DIR / f"retrieval_{time.strftime('%Y%m%d_%H%M%S')}.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"\n结果已写入 {out}")


if __name__ == "__main__":
    main()
```

> **已知限制**：`--golden` 复用模式在建索引时需要 chat_log，目前会建空索引。先支持"每次都传 --chat-log"的主路径，复用模式留到实际需要时再补。

- [ ] **Step 2: 生成合成示例**

`backend/golden/example_golden.jsonl`（**合成数据，不是真实聊天**）：

```
{"id":"q001","question":"你还记得我们第一次去海边是什么时候吗","evidence":"记得，是前年夏天，你非要在沙滩上堆城堡"}
{"id":"q002","question":"家里那只猫叫什么名字来着","evidence":"叫豆豆，是只橘猫，特别能吃"}
{"id":"q003","question":"我上次说想换工作你怎么看","evidence":"我觉得先别急，等年终奖发了再考虑"}
```

- [ ] **Step 3: 跑真实基线**

```powershell
cd backend
python -m evals.run --chat-log "C:\Users\Legion\Downloads\texts\私聊_妈妈.txt" --target 妈妈 --limit 40
```

记录输出的 `metrics`。

- [ ] **Step 4: 抽查 golden set 质量**

打开 `backend/golden/real_golden.jsonl`，人工看 10 条：

- 问题是不是真的在问过去的事？
- evidence 是不是真的回答了它？

把明显不对的比例记下来。**如果假阳性超过 3 成，回来调 `QUESTION_MARKERS`。**

- [ ] **Step 5: 提交**

```powershell
git add backend/evals/run.py backend/golden/example_golden.jsonl
git commit -m "feat: add retrieval evaluation CLI" -m "评估在临时 REUNION_HOME 下运行，不碰生产索引。每次输出带时间戳的 JSON 到 results/，作为后续改动的对比基线。附一份合成示例 golden set，真实数据不入库。"
git show --stat HEAD
```

**确认 `real_golden.jsonl` 和 `results/` 没有被提交。**

---

## 完成标准

- [ ] `python -m pytest -v` → 27 passed（18 + 9）
- [ ] `python -m evals.run ... --limit 40` 产出 `results/retrieval_*.json`
- [ ] `git show --stat` 确认真实语料与结果都没进 git
- [ ] 能口头回答：
  - 为什么 golden item 用 evidence 文本而不是 chunk id？
  - `recall@5` 和最终回复质量是什么关系？为什么不能只看最终回复？
  - 你的基线数字是多少？步骤 3 打算改进到什么程度？
