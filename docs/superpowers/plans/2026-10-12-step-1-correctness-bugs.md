# 步骤 1 — 正确性 bug 修复 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为「重逢」后端建立测试基础设施，修复三个已确认的正确性 bug，每个 bug 配一个先失败后通过的回归测试。

**Architecture:** 先引入 `REUNION_HOME` 环境变量让所有文件路径可重定向（当前所有路径硬编码到 `~/.reunion/`，导致代码无法测试）。然后逐 bug 走 TDD：写失败测试 → 确认失败 → 最小修复 → 确认通过 → 提交。三个 bug 有两个是同一个错误模式（**该合并的地方做了全量覆盖**），修复时统一用「合并语义」。

**Tech Stack:** Python 3.13 / FastAPI / pytest / ChromaDB / SQLite

**Spec:** `docs/superpowers/specs/2026-10-11-agent-engineering-roadmap-design.md`（§2.1 三个 bug、§4 步骤 1、§5.3 先正确性后优化）

## Global Constraints

- **产品定位**：完全本地运行、隐私优先。任何引入外部服务的改动都需要先讨论。
- **UI 文案**：温润极简，**不出现技术术语、红色错误图标、进度百分比**。后端错误信息会直接显示给用户，写人话。
- **Python 3.13**：运行时的联合类型语法（`X | None`）需要文件顶部 `from __future__ import annotations`。
- **不引入重型编排框架**，不引入 LangGraph。
- **学习模式**：构建者（桂子杰）写代码，Claude 出设计与 review。每个任务由构建者实现。
- **本步骤只修正确性，不做质量优化。** 召回率、人格相似度、延迟优化一律留给步骤 2 之后。
- **所有度量产出落盘**（§5.4）。本步骤的"度量"就是测试结果。
- 项目当前**没有任何测试**，`requirements.txt` 里也没有测试依赖。

## Review Focus

以下是 spec 隐含、但本计划的任务测试**不直接覆盖**的输入与失败模式，按"最可能咬到人"排序。每一条都在拥有对应代码的任务里加了一个测试。

1. **用户没走完 setup 就打开聊天窗口** —— `persona.md` 不存在时 `build_system_prompt` 收到空字符串。合理预期：不崩溃，且不能出现"记忆片段"相关内容。→ Task 1
2. **`config.json` 内容损坏（非法 JSON）** —— 整机重启后损坏的配置文件会让应用每次启动都崩。合理预期：降级为默认配置并保留坏文件供排查，而不是抛异常。→ Task 3
3. **聊天记录里找不到目标人物的消息** —— `extract_target_only` 返回空串，`setup.py` 会静默跳过记忆索引，接口仍返回 `ok`。合理预期：用户应被告知"没找到 TA 的发言"，而不是以为一切正常。→ Task 2
4. **`/api/settings` 并发写入** —— 两个请求同时改设置，后写的覆盖先写的。合理预期：至少不能丢字段。**未解决**，记录为已知缺口，步骤 4 引入写入门控时处理。
5. **API Key 无效或网络中断** —— `classify_intent` / 蒸馏调用抛异常。当前行为：`/api/chat` 返回 500 `对话失败: ...`，会把原始异常字符串暴露给用户（含英文技术信息）。**未解决**，记录为已知缺口，属于 §2.2「错误处理」范畴，留到步骤 2。

---

## 文件结构

| 文件 | 职责 | 动作 |
|------|------|------|
| `backend/requirements-dev.txt` | 开发依赖（pytest） | 新建 |
| `backend/pytest.ini` | pytest 配置 | 新建 |
| `backend/tests/__init__.py` | 让 tests 成为包 | 新建 |
| `backend/tests/conftest.py` | 注入 `REUNION_HOME`、把 `backend/` 加进 `sys.path` | 新建 |
| `backend/tests/test_agent_prompt.py` | bug #1 回归测试 | 新建 |
| `backend/tests/test_store.py` | bug #2 回归测试 | 新建 |
| `backend/tests/test_settings.py` | bug #3 回归测试 | 新建 |
| `backend/config.py` | 路径可重定向 | 修改 |
| `backend/agent/loop.py` | bug #1 修复 | 修改 |
| `backend/rag/store.py` | bug #2 修复 | 修改 |
| `backend/api/setup.py` | bug #2 调用点 + 空记忆提示 | 修改 |
| `backend/api/settings.py` | bug #3 修复 | 修改 |
| `docs/decisions/` | ADR 决策日志（§5.1） | 新建 |
| `README.md` | 7 段骨架（§4 步骤 9 注） | 修改 |

---

### Task 1: 测试基础设施 + 修 bug #1（guardrail 与检索打架）

**背景（bug #1）**：`GUARDRAIL` 要求"只依据下方「记忆片段」中的内容回答，没有就说记不太清了"，但 `agent/loop.py:89-92` 只在 `memory_search` 意图下才检索记忆。闲聊时 `memories=[]`，`build_system_prompt` 仍会拼上 `（暂无相关记忆）` 和那段 guardrail —— 等于在命令人格"你现在失忆了"。

**修复方向**：guardrail 拆成两段。**基础段**永远存在（禁止编造）；**记忆段**只在真的检索到记忆时才拼进去。**约束只在它的前提成立时才生效。**

**Files:**
- Create: `backend/requirements-dev.txt`、`backend/pytest.ini`、`backend/tests/__init__.py`、`backend/tests/conftest.py`、`backend/tests/test_agent_prompt.py`
- Modify: `backend/config.py:1-8`、`backend/agent/loop.py:9-20`

**Interfaces:**
- Consumes: 无（第一个任务）
- Produces:
  - `config.DATA_DIR: Path` —— 现在读环境变量 `REUNION_HOME`，默认 `Path.home() / ".reunion"`
  - `agent.loop.build_system_prompt(persona: str, memories: list[str]) -> str`
  - 测试基础设施：`backend/pytest.ini`，从 `backend/` 目录运行 `python -m pytest` 即可

- [ ] **Step 0: 开分支**

当前在 `master`，先隔离。

```bash
cd /d/重逢2
git checkout -b step-1-correctness-bugs
```

- [ ] **Step 1: 新建开发依赖文件**

Create `backend/requirements-dev.txt`:

```
-r requirements.txt
pytest>=8.0
```

安装：

```bash
pip install -r backend/requirements-dev.txt
```

- [ ] **Step 2: 让文件路径可重定向**

现在 `config.py` 把路径硬编码到 `~/.reunion/`，测试一跑就会污染真实用户数据。改成读环境变量。

Modify `backend/config.py` 顶部（第 1-8 行）：

```python
import json
import os
from pathlib import Path

DATA_DIR = Path(os.environ.get("REUNION_HOME", str(Path.home() / ".reunion")))
CONFIG_PATH = DATA_DIR / "config.json"
PERSONA_PATH = DATA_DIR / "persona.md"
AVATAR_PATH = DATA_DIR / "avatar.png"
```

注意 `os.environ.get` 的默认值写成了 `str(...)` 再交给 `Path()` —— 环境变量一定是字符串，两条分支保持一致。

- [ ] **Step 3: 新建 pytest 配置**

Create `backend/pytest.ini`:

```ini
[pytest]
testpaths = tests
pythonpath = .
```

`pythonpath = .` 需要 pytest >= 7（我们装的是 8）。它让 `from config import ...` 这类顶层导入在 `backend/` 下能解析。

- [ ] **Step 4: 新建 conftest，注入测试用数据目录**

Create `backend/tests/__init__.py`（空文件）。

Create `backend/tests/conftest.py`:

```python
"""测试全局配置。

关键：REUNION_HOME 必须在**任何项目模块被导入之前**设置，
因为 config.py 在模块级就把路径算好了。conftest.py 的导入
早于测试模块的收集，所以在文件顶部设置是安全的。
"""

import os
import tempfile
from pathlib import Path

# 每个测试会话一个全新的临时目录，测试结束不会污染 ~/.reunion/
_TEST_HOME = Path(tempfile.mkdtemp(prefix="reunion-test-"))
os.environ["REUNION_HOME"] = str(_TEST_HOME)
```

（模块搜索路径由 `pytest.ini` 的 `pythonpath = .` 负责，这里不重复处理。）

- [ ] **Step 5: 写 bug #1 的失败测试**

Create `backend/tests/test_agent_prompt.py`:

```python
from agent.loop import build_system_prompt

PERSONA = "# 妈妈 — Relationship Persona\n\n说话简短，爱用「嗯」。"


def test_persona_always_present():
    """无论有没有记忆，人格设定都必须出现。"""
    assert PERSONA in build_system_prompt(PERSONA, [])


def test_no_memory_section_when_no_memories():
    """bug #1 回归：没有检索到记忆时，不得出现任何「记忆」相关指令。

    旧实现会拼上「（暂无相关记忆）」和「只依据记忆片段回答，没有就说记不太清了」，
    等于在闲聊时命令人格失忆。
    """
    prompt = build_system_prompt(PERSONA, [])

    assert "记忆片段" not in prompt
    assert "记不太清了" not in prompt
    assert "暂无相关记忆" not in prompt


def test_memory_section_present_when_memories_exist():
    """检索到记忆时，记忆内容和约束都要出现。"""
    prompt = build_system_prompt(PERSONA, ["用户和妈妈一起去过海边"])

    assert "用户和妈妈一起去过海边" in prompt
    assert "记不太清了" in prompt


def test_never_fabricate_rule_always_present():
    """禁止编造这条约束与记忆无关，必须永远存在。"""
    for memories in ([], ["用户去过海边"]):
        assert "绝不编造" in build_system_prompt(PERSONA, memories)


def test_empty_persona_does_not_crash():
    """Review Focus #1：用户没走完 setup 就打开聊天窗口。

    合理预期：不崩溃，且不出现记忆相关内容。
    """
    prompt = build_system_prompt("", [])

    assert isinstance(prompt, str)
    assert "记忆片段" not in prompt
```

- [ ] **Step 6: 跑测试，确认失败**

```bash
cd /d/重逢2/backend
python -m pytest tests/test_agent_prompt.py -v
```

Expected: `test_no_memory_section_when_no_memories` FAIL（"记忆片段" 出现在 prompt 里）；`test_empty_persona_does_not_crash` 也可能 FAIL。其余通过。

- [ ] **Step 7: 修 bug #1**

Modify `backend/agent/loop.py` 第 9-20 行，把单个 `GUARDRAIL` 换成两段：

```python
GUARDRAIL = """
## 重要规则
- 绝不编造不存在的记忆、经历或事实。
- 用自然、口语化的方式回应，就像日常聊天一样。
"""

MEMORY_GUARDRAIL = """
## 关于下方「记忆片段」
这些片段是从真实聊天记录中检索出来的相关往事。
- 提到过去的事时，只依据这些片段，不要补充片段里没有的细节。
- 如果用户问起的事不在片段中，就坦诚地说「记不太清了」或「我好像想不起来了」。
"""


def build_system_prompt(persona: str, memories: list[str]) -> str:
    """组装 System Prompt。

    记忆段只在真的检索到记忆时才拼接 —— 约束只在它的前提成立时才生效。
    """
    if not memories:
        return f"{persona}\n\n{GUARDRAIL}"

    memory_text = "\n".join(f"- {m}" for m in memories)
    return f"{persona}\n\n{GUARDRAIL}\n\n{MEMORY_GUARDRAIL}\n\n## 记忆片段\n{memory_text}"
```

- [ ] **Step 8: 跑测试，确认通过**

```bash
cd /d/重逢2/backend
python -m pytest tests/test_agent_prompt.py -v
```

Expected: 5 passed。

- [ ] **Step 9: 提交**

```bash
cd /d/重逢2
git add backend/requirements-dev.txt backend/pytest.ini backend/tests/ backend/config.py backend/agent/loop.py
git commit -m "fix: apply memory guardrail only when memories were retrieved

GUARDRAIL 要求只依据记忆片段回答，但记忆仅在 memory_search 意图下才检索。
闲聊时 memories 为空，系统提示词实际在命令人格失忆。

同时引入 REUNION_HOME 环境变量让数据目录可重定向，否则测试会污染
真实的 ~/.reunion/ 数据。"
```

---

### Task 2: 修 bug #2（向量库被静默清空）

**背景（bug #2）**：`rag/store.py:24-29` 的函数叫 `get_or_create_collection`，但它**先 `delete_collection` 再 `create_collection`**。函数名在撒谎 —— 任何人读到这个名字都会以为它幂等。同时，`api/setup.py:79` 直接在索引流程里调用它，一旦 `collection.add` 失败，旧记忆已经被删掉了。

**修复方向**：拆成两个名字诚实的函数。`get_or_create_collection` 真的只获取或创建；破坏性操作变成显式的 `reset_collection`，并注明只应在重新 onboarding 时调用。

**Files:**
- Modify: `backend/rag/store.py:24-39`、`backend/api/setup.py:74-86`
- Create: `backend/tests/test_store.py`

**Interfaces:**
- Consumes: `config.DATA_DIR`（Task 1 已改为可重定向）
- Produces:
  - `rag.store.get_or_create_collection(name: str = "memories")` —— **非破坏性**
  - `rag.store.reset_collection(name: str = "memories")` —— **破坏性**，清空并重建
  - `rag.store.query_collection(query_embedding: list[float], n_results: int = 5) -> list[str]`

- [ ] **Step 1: 读现有 RAG 层**

通读这三个文件，它们是整个 RAG 层的全部（共 124 行）：

```
backend/rag/chunker.py    (64 行)
backend/rag/embedder.py   (21 行)
backend/rag/store.py      (39 行)
```

对照你在 `D:\rag-practice\` 里手搓的版本，回答三个问题（写进 ADR）：

1. `get_or_create_collection` 的行为和它的名字一致吗？
2. `query_collection` 里的 `except Exception: return []` 会吞掉哪些错误？把"数据库损坏"和"还没有记忆"变成同一个结果，有什么风险？
3. `chunker.py` 的 `chunk_size=512` 是字符还是 token？对照你在探针里测到的 `max_seq_length=512`，这个值合适吗？（**本步骤不改它** —— 那属于步骤 3 的质量优化，先记下来。）

- [ ] **Step 2: 写 bug #2 的失败测试**

Create `backend/tests/test_store.py`:

```python
import pytest

from rag import store

DIM = 4  # 测试用极小维度，快且够用


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
```

- [ ] **Step 3: 跑测试，确认失败**

```bash
cd /d/重逢2/backend
python -m pytest tests/test_store.py -v
```

Expected: `test_get_or_create_is_not_destructive` FAIL（count 变成 0）；`test_reset_collection_clears_data` FAIL（`reset_collection` 还不存在 → AttributeError）。

- [ ] **Step 4: 修 bug #2**

Modify `backend/rag/store.py`，把第 24-39 行替换为：

```python
def _existing_names(client) -> set[str]:
    return {c.name for c in client.list_collections()}


def get_or_create_collection(name: str = "memories"):
    """获取 collection，不存在才创建。**非破坏性** —— 不碰已有数据。"""
    client = get_client()
    if name in _existing_names(client):
        return client.get_collection(name)
    return client.create_collection(name=name, metadata={"hnsw:space": "cosine"})


def reset_collection(name: str = "memories"):
    """清空并重建 collection。**破坏性操作** —— 只应在重新 onboarding 时调用。"""
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
```

注意 `query_collection` 不再用 `except Exception` —— 它现在只把「collection 不存在」当作"还没有记忆"，其他异常照常抛出。**把不同原因的错误折叠成同一个结果，是在制造静默失败。**

- [ ] **Step 5: 跑测试，确认通过**

```bash
cd /d/重逢2/backend
python -m pytest tests/test_store.py -v
```

Expected: 5 passed。

- [ ] **Step 6: 改调用点 + 空记忆提示**

Modify `backend/api/setup.py` 第 74-86 行，`get_or_create_collection` 改为 `reset_collection`，并处理 `extract_target_only` 返回空串的情况（Review Focus #3）：

```python
        # Chunk and embed target's messages
        try:
            target_text = extract_target_only(req.chat_log, req.name)
            if not target_text.strip():
                raise HTTPException(
                    status_code=400,
                    detail=f"在聊天记录里没有找到「{req.name}」说的话，换一份记录再试试",
                )
            chunks = chunk_text(target_text)
            embeddings = embed_texts(chunks)
            collection = reset_collection("memories")
            collection.add(
                documents=chunks,
                embeddings=embeddings,
                ids=[f"mem_{i}" for i in range(len(chunks))],
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"记忆索引失败: {str(e)}")
```

同时修改 `backend/api/setup.py` 第 7 行的 import：

```python
from rag.store import reset_collection
```

`except HTTPException: raise` 是必需的 —— 否则我们刚抛的那个 400 会被下面的 `except Exception` 抓住、包装成 500。

- [ ] **Step 7: 手动验证空记忆分支**

```bash
cd /d/重逢2/backend
python -c "from rag.chunker import extract_target_only; print(repr(extract_target_only('2024-01-01 10:00 小明\n你好', '妈妈')))"
```

Expected: `''`（空字符串）—— 证明当目标人物没发言时确实会走到新加的分支。

- [ ] **Step 8: 提交**

```bash
cd /d/重逢2
git add backend/rag/store.py backend/api/setup.py backend/tests/test_store.py
git commit -m "fix: make get_or_create_collection non-destructive

函数名撒谎：get_or_create_collection 实际执行 delete + create，
重新索引时会把已有记忆全部清空。拆成非破坏性的
get_or_create_collection 和显式的 reset_collection。

同时修掉 query_collection 的 except Exception —— 它把
「数据库损坏」和「还没有记忆」折叠成同一个返回值。"
```

---

### Task 3: 修 bug #3（设置保存时丢失字段 + 静默失败）

**背景（bug #3）**：`api/settings.py:52-60` 用一个只含 6 个键的新 dict 覆盖整个 `config.json`。`has_avatar`、`last_seen`、`birth_info` 不在里面，用户只要改一次设置，这三个字段就**永久消失**。同一函数第 66 行还有 `except Exception: pass`，人格合并失败完全无声。

**这是与 bug #2 相同的错误模式**：该合并的地方做了全量覆盖。

**Files:**
- Modify: `backend/api/settings.py:1-11, 37-68`
- Create: `backend/tests/test_settings.py`

**Interfaces:**
- Consumes: `config.load_config()`、`config.save_config()`、`config.PERSONA_PATH`（Task 1 已可重定向）
- Produces: 无新增公开接口，仅修正 `PUT /api/settings` 的行为

- [ ] **Step 1: 写 bug #3 的失败测试**

Create `backend/tests/test_settings.py`:

```python
import asyncio
import json

from api import settings
from config import CONFIG_PATH, load_config, save_config


def _put(**fields):
    """直接调用 async 端点，避免引入 pytest-asyncio。"""
    return asyncio.run(settings.update_settings(settings.SettingsUpdate(**fields)))


def _fresh_config():
    save_config({
        "api_key": "sk-test",
        "name": "妈妈",
        "your_name": "小明",
        "relationship": "母子",
        "personality": "话少",
        "extra": "",
        "has_avatar": True,
        "last_seen": "2024-01-15",
        "birth_info": "1965",
    })


def test_update_preserves_unrelated_fields():
    """bug #3 回归：改设置不能丢掉 has_avatar / last_seen / birth_info。"""
    _fresh_config()

    _put(name="妈妈", personality="话很少，但很细心")

    cfg = load_config()
    assert cfg["has_avatar"] is True
    assert cfg["last_seen"] == "2024-01-15"
    assert cfg["birth_info"] == "1965"


def test_update_applies_changed_fields():
    """改动本身要生效。"""
    _fresh_config()

    _put(name="妈妈", personality="话很少，但很细心")

    assert load_config()["personality"] == "话很少，但很细心"


def test_empty_field_keeps_existing_value():
    """请求里没填的字段保持原值，不能被空字符串清掉。"""
    _fresh_config()

    _put(name="妈妈", personality="")

    assert load_config()["personality"] == "话少"


def test_masked_api_key_is_not_written_back():
    """前端回传打码的 key 时，必须保留真实 key。"""
    _fresh_config()

    _put(name="妈妈", api_key="sk-test****")

    assert load_config()["api_key"] == "sk-test"


def test_corrupt_config_falls_back_to_defaults():
    """Review Focus #2：config.json 损坏时不能让应用启动即崩。

    合理预期：降级为默认值，并把坏文件改名保留供排查。
    """
    CONFIG_PATH.write_text("{ 这不是合法 JSON", encoding="utf-8")

    assert load_config() == {}
    assert list(CONFIG_PATH.parent.glob("config.json.corrupt*")), "坏文件应被保留"
```

- [ ] **Step 2: 跑测试，确认失败**

```bash
cd /d/重逢2/backend
python -m pytest tests/test_settings.py -v
```

Expected: `test_update_preserves_unrelated_fields` FAIL（`has_avatar` 丢失）；`test_corrupt_config_falls_back_to_defaults` FAIL（`load_config` 抛 `JSONDecodeError`）。

- [ ] **Step 3: 让 load_config 容忍损坏的配置**

Modify `backend/config.py`，替换 `load_config`：

```python
def load_config() -> dict:
    ensure_data_dir()
    if not CONFIG_PATH.exists():
        return {}
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        # 配置损坏不该让应用启动即崩。保留坏文件供排查，降级为默认配置。
        broken = CONFIG_PATH.with_suffix(f".json.corrupt-{int(time.time())}")
        CONFIG_PATH.replace(broken)
        return {}
```

并在 `backend/config.py` 顶部补 `import time`。

- [ ] **Step 4: 修 bug #3 的覆盖问题**

Modify `backend/api/settings.py` 第 1-11 行，加 logger：

```python
import logging
import shutil
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel

from config import load_config, save_config, PERSONA_PATH, AVATAR_PATH, DATA_DIR
from persona.distiller import merge_persona

logger = logging.getLogger(__name__)

router = APIRouter()
```

Modify `update_settings`（第 37-68 行）：

```python
@router.put("/api/settings")
async def update_settings(req: SettingsUpdate):
    config = load_config()
    api_key = req.api_key if req.api_key and "****" not in req.api_key else config.get("api_key", "")

    updated = {}
    for field in ("name", "personality", "extra", "relationship"):
        value = getattr(req, field)
        if value and value != config.get(field):
            updated[field] = value

    # 合并而不是覆盖：保留所有本次未提及的字段（has_avatar / last_seen / birth_info 等）
    merged = dict(config)
    merged["api_key"] = api_key
    for field in ("name", "your_name", "relationship", "personality", "extra"):
        value = getattr(req, field)
        if value:
            merged[field] = value
    save_config(merged)

    if updated and PERSONA_PATH.exists() and api_key:
        try:
            merge_persona(updated, api_key)
        except Exception:
            logger.exception("人格增量合并失败；设置已保存，但 persona.md 未更新")

    return {"status": "ok"}
```

两处关键改动：
- `merged = dict(config)` 保留全部既有字段 —— 这是 bug #3 的核心修复
- `except Exception: pass` → `logger.exception(...)`。**失败仍然不算致命（设置本身存下来了），但不能再无声。**

> **本步骤刻意不改的地方**：`merge_persona` 是同步阻塞调用，放在 `async def` 端点里会卡住整个事件循环（一次 LLM 调用几秒钟）。`api/chat.py:33` 调 `agent_chat` 有同样的问题。但这属于 **步骤 6（流式 + 异步）** 的范围，不是正确性 bug。**先别顺手修它 —— 那正是「先正确性，后优化」要防的事。**

- [ ] **Step 5: 跑测试，确认通过**

```bash
cd /d/重逢2/backend
python -m pytest tests/test_settings.py -v
```

Expected: 5 passed。

- [ ] **Step 6: 提交**

```bash
cd /d/重逢2
git add backend/config.py backend/api/settings.py backend/tests/test_settings.py
git commit -m "fix: merge settings instead of overwriting config

PUT /api/settings 用只含 6 个键的新 dict 覆盖整个 config.json，
导致 has_avatar / last_seen / birth_info 在用户改任意设置后被永久清除。
与 store.py 的 collection 重建是同一个错误模式：该合并的地方做了全量覆盖。

顺带把 merge_persona 的静默 except 换成 logger.exception，
并让 load_config 容忍损坏的 config.json。"
```

---

### Task 4: 全量回归 + ADR + README 骨架

**Files:**
- Create: `docs/decisions/0001-*.md` ~ `0004-*.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: Task 1-3 的全部产出
- Produces: `docs/decisions/` 目录约定（后续每个决定一条 ADR）

- [ ] **Step 1: 跑全量测试**

```bash
cd /d/重逢2/backend
python -m pytest -v
```

Expected: 15 passed（5 + 5 + 5）。

如果失败，**停下来修**，不要继续。

- [ ] **Step 2: 确认真实用户数据没被污染**

```bash
ls ~/.reunion/
```

Expected: 内容与本次测试前一致 —— 测试全部写在临时目录里。

- [ ] **Step 3: 建立 ADR 决策日志**

Create `docs/decisions/0001-adopt-adr.md`:

```markdown
# ADR-0001：采用 ADR 记录技术决策

- 日期：2026-10-12
- 状态：已采纳

## 背景

README 的「取舍」段（选了 A 否决了 B 及原因）是作品评审的重点，
但决策的上下文会随时间流失。事后靠回忆重构必然遗漏最有价值的细节。

## 决定

在 `docs/decisions/` 下，每个技术决策一个文件，编号递增。
格式：日期 / 状态 / 背景 / 备选方案 / 决定 / 理由 / 后果。
决策发生时立即记录，不等最后补写。

## 后果

- README 的「取舍」段从 ADR 自然长出，不靠回忆
- 面试时能复述决策的上下文，而不只是结论
```

Create `docs/decisions/0002-guardrail-is-conditional.md`:

```markdown
# ADR-0002：记忆约束改为条件式

- 日期：2026-10-12
- 状态：已采纳

## 背景

GUARDRAIL 要求「只依据记忆片段回答，没有就说记不太清了」，
但记忆检索只在 memory_search 意图下发生。闲聊时 memories 为空，
系统提示词却在命令人格失忆 —— 约束的前提不成立，约束本身变成了 bug。

## 备选方案

1. **取消意图门控，每条消息都检索记忆** —— 修真了前提，但每条消息都多一次
   向量检索（延迟 + 成本），而它解决的问题属于检索质量，不是正确性。
2. **把约束改成条件式** —— 只在真的检索到记忆时才拼接记忆段。

## 决定

方案 2。

## 理由

符合「先正确性，后优化」的纪律。方案 1 是**优化**（提升记忆召回），
它需要步骤 2 的度量才能判断是否值得。方案 2 是**正确性修复**，不需要度量。

## 后果

- 闲聊时人格不再被告知失忆
- 方案 1 留到步骤 4（tool calling）重新评估 —— 那时记忆检索会变成工具，
  由模型自己决定何时调用，比意图分类更灵活
```

Create `docs/decisions/0003-explicit-destructive-operations.md`:

```markdown
# ADR-0003：破坏性操作必须显式命名

- 日期：2026-10-12
- 状态：已采纳

## 背景

`get_or_create_collection` 这个名字承诺幂等，实际执行 delete + create。
api/setup.py 的索引流程直接调用它，一旦 collection.add 失败，
旧记忆已经被删掉。同一个错误模式在 api/settings.py 又出现一次：
PUT 用全量覆盖代替合并，丢掉了 has_avatar / last_seen / birth_info。

## 决定

- 函数名必须描述真实行为。破坏性操作单独命名（`reset_collection`），
  并在 docstring 里标明调用时机。
- 部分更新一律用**合并**语义，不用全量覆盖。

## 后果

- 需要清空记忆时，调用者必须显式选择破坏性 API，不能被名字骗到
- 步骤 4 引入工具调用时，工具列表里必须区分读工具与写/删工具
  （调研结论：权限设计应当 deny-first）
```

Create `docs/decisions/0004-reunion-home-env-var.md`:

```markdown
# ADR-0004：用 REUNION_HOME 让数据目录可重定向

- 日期：2026-10-12
- 状态：已采纳

## 背景

所有路径硬编码到 `~/.reunion/`，且是模块级常量。任何测试一跑就会
污染真实用户数据 —— 而真实数据是用户导入的已故亲人聊天记录，
污染它是不可接受的。

## 备选方案

1. **每个测试 monkeypatch 各个模块里的路径常量** —— 因为
   `from config import DATA_DIR` 在每个模块里制造了独立绑定，
   需要逐个 patch，易漏且脆弱。
2. **环境变量 `REUNION_HOME`**，在 config.py 模块级读取。

## 决定

方案 2。测试的 conftest.py 在导入任何项目模块之前把它指向临时目录。

## 理由

一处定义，全局生效。同时它也是打包分发时的标准做法
（用户可自定义数据位置）。

## 后果

- 测试完全隔离，不碰真实数据
- 前提：环境变量必须在项目模块被导入前设置。conftest.py 顶部设置即可，
  因为 conftest 的导入早于测试模块的收集
```

- [ ] **Step 4: 建立 README 骨架**

README 现在是功能说明，按 spec §4 步骤 9 改成 7 段**设计文档**结构。**本步骤只建骨架**，数字段留空标 TBD，等步骤 2-8 的实测填充。

在 `README.md` 顶部（现有内容之前）插入：

```markdown
# 重逢 — AI 数字亲人桌面伴侣

> 📐 本 README 按设计文档结构组织：问题 → 约束 → 架构 → 度量方式 → 数字 → 取舍 → 下一步

## 1. 问题

让没有任何编程经验的普通人，也能通过导入与已故亲人的聊天记录，
生成本地运行的专属 AI 数字亲人。

## 2. 约束

| 约束 | 对技术选型的影响 |
|------|-----------------|
| 完全本地运行、隐私优先 | 可观测性必须自托管（Langfuse，不用 LangSmith） |
| 面向零技术背景用户 | 错误信息必须是中文人话，不暴露堆栈 |
| 单机桌面环境 | 不引入需要外部服务的依赖 |

## 3. 架构

<!-- TBD：步骤 3 后补 Mermaid 架构图 -->

## 4. 怎么度量的

<!-- TBD：步骤 2 建立 eval harness 后填写 -->

## 5. 数字

<!-- TBD：步骤 2-8 的实测数据。当前进度见 docs/superpowers/plans/ -->

## 6. 取舍

详见 `docs/decisions/`。已记录的决策：

- [ADR-0002](docs/decisions/0002-guardrail-is-conditional.md) — 记忆约束改为条件式
- [ADR-0003](docs/decisions/0003-explicit-destructive-operations.md) — 破坏性操作必须显式命名

## 7. 下一步

见 `docs/superpowers/specs/2026-10-11-agent-engineering-roadmap-design.md`。
```

- [ ] **Step 5: 提交**

```bash
cd /d/重逢2
git add docs/decisions/ README.md
git commit -m "docs: add ADR log and restructure README as design doc

README 从功能说明改为 7 段设计文档骨架（问题/约束/架构/度量方式/
数字/取舍/下一步）。数字段留 TBD，等步骤 2-8 的实测填充。

docs/decisions/ 开始记录 ADR，README 的「取舍」段将从这里长出。"
```

---

## 完成标准

全部满足才算步骤 1 结束：

- [ ] `cd backend && python -m pytest -v` → 15 passed
- [ ] `~/.reunion/` 未被测试污染
- [ ] 三个 bug 各有一个**先失败后通过**的回归测试（可从 commit 历史验证）
- [ ] `docs/decisions/` 有 4 条 ADR
- [ ] README 有 7 段骨架，数字段明确标 TBD
- [ ] 能口头回答：三个 bug 里哪两个是同一个错误模式？为什么先修它们而不先优化 RAG？
