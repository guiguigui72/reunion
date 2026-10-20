# ADR-0003：破坏性操作必须显式命名

- 日期：2026-10-19
- 状态：已采纳

## 背景

同一个错误模式在项目中出现了三次：**该合并的地方做了全量覆盖。**

1. `rag/store.py` 的 `get_or_create_collection` —— 名字承诺幂等，实际执行 `delete` + `create`。
   `api/setup.py` 在索引流程里直接调用它，一旦 `add` 失败，旧记忆已经没了。
2. `api/settings.py` 的 `update_settings` —— 用只含 6 个键的新 dict 覆盖整个 `config.json`，
   丢掉 `has_avatar` / `last_seen` / `birth_info`。
3. `rag/store.py` 的 `query_collection` —— `except Exception: return []`，
   把「数据库损坏」和「还没有记忆」折叠成同一个结果。

## 决定

- **函数名必须描述真实行为。** 破坏性操作单独命名（`reset_collection`），
  并在 docstring 里标明调用时机与后果。
- **部分更新一律用合并语义** —— 先复制完整数据，再改指定字段，不用全量覆盖。
- **捕获异常要精确。** 只捕获你真正想处理的那一种；写 `except Exception` 之前先问
  「我到底想捕获什么」。

## 理由

- **名字在撒谎比没有名字更危险**：读代码的人会放心调用，然后数据就没了。
- 合并语义让「未提及的字段自动保留」成为默认行为，不需要每次枚举全部字段。
- 精确捕获让不同原因的错误保持可区分，避免静默失败。

## 后果

- 需要清空记忆时，调用者必须显式选择 `reset_collection`，名字本身就在警告他
- 步骤 4 引入 tool calling 时，工具列表里必须区分读工具与写/删工具（权限设计 deny-first）
- 回归测试：`backend/tests/test_store.py`、`backend/tests/test_settings.py`

## 已知限制

`SettingsUpdate` 的字段默认是 `""`，服务端无法区分「没传这个字段」和「传了空字符串想清空」。
所以目前**无法通过接口清空某个字段**。

彻底修复需要把字段改成 `Optional[str] = None`，并用 `req.model_fields_set` 判断哪些字段真的被传了。
留待后续处理。
