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
    """判断一句话是否值得作为检索评估的问题。

    强标记（疑问词）够 4 个字就收；
    弱标记（"吗"/"？"）必须够长 —— 否则"是吗？"这类对白里的附会
    混进评估集，测的就不是检索能力了。
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
