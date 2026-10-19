import pytest

from rag import store

DIM = 4  # 测试用极小维度，快且够用

#每一个测试函数运行前都会调用这个函数
@pytest.fixture(autouse=True)
def _clean_store():
    """每个测试前清空所有 collection。

    五个测试共用同一个临时数据目录，不清空的话先跑的测试会写进
    memories，导致后面「collection 不存在」的测试拿到非空结果。
    """
    client = store.get_client()
    for col in client.list_collections():
        client.delete_collection(col.name)
    yield


def _vec(seed: float) -> list[float]:
    return [seed, seed, seed, seed]


def test_get_or_create_is_not_destructive():
    """bug #2 回归：再取一次同名 collection，数据必须还在。

    旧实现每次都 delete + create，第二次调用会把已写入的记忆清空。
    """
    col = store.get_or_create_collection("memories")
    col.add(documents=["用户和妈妈去过海边"], ids=["m1"], embeddings=[_vec(0.1)])
    assert col.count() == 1

    again = store.get_or_create_collection("memories")

    assert again.count() == 1, "get_or_create_collection 不应清空已有数据"


def test_get_or_create_is_idempotent():
    """同一个 collection 反复获取，id 必须稳定。"""
    first = store.get_or_create_collection("memories").id
    second = store.get_or_create_collection("memories").id
    assert first == second


def test_reset_collection_clears_data():
    """显式的破坏性操作确实要清空。"""
    col = store.get_or_create_collection("memories")
    col.add(documents=["旧记忆"], ids=["m1"], embeddings=[_vec(0.2)])
    assert col.count() == 1

    store.reset_collection("memories")

    assert store.get_or_create_collection("memories").count() == 0


def test_reset_collection_on_missing_collection_does_not_raise():
    """对不存在的 collection 调 reset 不应报错。"""
    store.reset_collection("never_created")


def test_query_collection_returns_empty_when_no_collection():
    """还没有记忆时返回空列表，而不是抛异常。"""
    assert store.query_collection(_vec(0.3), n_results=3) == []

