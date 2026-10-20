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
    """「嗯」太短，不承载可检索信息，应被跳过。"""
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


def test_build_golden_skips_vague_questions():
    """「是吗？」这类附和不是检索需求，不该进评估集。"""
    chat = (
        "2024-01-01 10:00 '我'\n是吗？\n"
        "2024-01-01 10:01 '妈妈'\n记得啊，那天特别冷\n"
    )
    assert build_golden(chat, "妈妈") == []


def test_short_question_with_strong_marker_is_kept():
    """"什么时候去的"只有 6 个字，但有疑问词，应该保留。"""
    chat = (
        "2024-01-01 10:00 '我'\n什么时候去的\n"
        "2024-01-01 10:01 '妈妈'\n去年春天吧，花开得正好\n"
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
