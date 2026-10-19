from __future__ import annotations

import chromadb
from chromadb.config import Settings

from config import DATA_DIR, ensure_data_dir

CHROMA_DIR = str(DATA_DIR / "chroma")

_client: chromadb.PersistentClient | None = None


def get_client() -> chromadb.PersistentClient:
    global _client
    if _client is None:
        ensure_data_dir()
        _client = chromadb.PersistentClient(
            path=CHROMA_DIR,
            settings=Settings(anonymized_telemetry=False),
        )
    return _client


def _existing_names(client) -> set[str]:
    """列出当前所有 collection 的名字。"""
    return {c.name for c in client.list_collections()}


def get_or_create_collection(name: str = "memories"):
    """获取 collection，不存在才创建。

    **非破坏性** —— 不碰已有数据。反复调用返回同一个 collection。
    """
    client = get_client()
    if name in _existing_names(client):
        return client.get_collection(name)
    return client.create_collection(name=name, metadata={"hnsw:space": "cosine"})


def reset_collection(name: str = "memories"):
    """清空并重建 collection。

    **破坏性操作** —— 会删除该 collection 的全部数据。
    只应在用户重新走 onboarding（导入新的聊天记录）时调用。
    """
    client = get_client()
    if name in _existing_names(client):
        client.delete_collection(name)
    return client.create_collection(name=name, metadata={"hnsw:space": "cosine"})


def query_collection(query_embedding: list[float], n_results: int = 5) -> list[str]:
    """检索相关记忆。collection 还不存在时返回空列表。"""
    client = get_client()
    if "memories" not in _existing_names(client):
        return []

    col = client.get_collection("memories")
    results = col.query(query_embeddings=[query_embedding], n_results=n_results)
    return results["documents"][0] if results["documents"] else []