"""检索评估：建索引、跑查询、算指标。"""
from __future__ import annotations

from evals.golden import evidence_key
from rag.chunker import (
    chunk_text,
    extract_target_only,
    extract_target_with_context,
)
from rag.embedder import embed_texts
from rag.store import query_collection, reset_collection

EXTRACTORS = {
    "plain": extract_target_only,
    "contextual": extract_target_with_context,
}

def recall_at_k(retrieved: list[str], evidence: str, k: int) -> bool:
    """top-k 结果里是否包含证据。"""
    key = evidence_key(evidence)
    return any(key in doc for doc in retrieved[:k])


def mrr(retrieved: list[str], evidence: str) -> float:
    """第一个命中位置的倒数；没命中为 0。"""
    key = evidence_key(evidence)
    for rank, doc in enumerate(retrieved, start=1):
        if key in doc:
            return 1.0 / rank
    return 0.0


def build_index(
    chat_log: str,
    target_name: str,
    extractor: str = "contextual",
) -> tuple[int, int]:
    """用与生产相同的管线建索引。extractor 决定块里带不带对话语境。"""
    if extractor not in EXTRACTORS:
        raise ValueError(f"未知的 extractor: {extractor}")

    target_text = EXTRACTORS[extractor](chat_log, target_name)
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
    return query_collection(embed_texts([question])[0], n_results=n_results)


def score_all(
    items: list[dict],
    retrieved_map: dict[str, list[str]],
    ks: tuple[int, ...] = (1, 5),
) -> dict:
    """汇总指标。返回值为 0-1 的比例。"""
    metrics: dict[str, float] = {f"recall@{k}": 0.0 for k in ks}
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
