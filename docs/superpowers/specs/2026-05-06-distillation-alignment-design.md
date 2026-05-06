# 重逢 — 蒸馏引擎 dot-skill 对齐 设计规范

## 问题

当前蒸馏效果差，根因是我们自己写了一个分析 prompt，没有使用 dot-skill 原生成熟的 `persona_analyzer.md` 和 `persona_builder.md`。dot-skill 的 prompt 是字段化填表逻辑，我们的实现变成了开放式文章生成。

## 改造目标

严格对齐 dot-skill relationship 家族的蒸馏流水线，使用其原生 prompt 文件，仅将交互式 intake 替换为我们的表单数据。

## dot-skill 原生流水线

```
intake.md（AI Agent 跟用户对话收集信息）
    ↓
persona_analyzer.md（LLM 分析 → 结构化字段输出）
    ↓
persona_builder.md（填入模板 → LLM 生成 6 层 persona.md）
```

## 重逢适配流水线

```
表单数据（Step 1a/1b/1c） + 聊天记录
    ↓  替代 intake.md
persona_analyzer.md（使用 dot-skill 原生 prompt）
    ↓  结构化字段
解析字段 → 填入 persona_builder.md 模板
    ↓
persona_builder.md（使用 dot-skill 原生 prompt）
    ↓
6 层 persona.md（含 4 类例句）
```

---

## 实现细节

### Step 1: 格式化输入喂给 persona_analyzer.md

**不改 prompt 内容**，只组织输入格式使之匹配 prompt 的预期。

`persona_analyzer.md` 预期接收：
```
1. manually provided relationship context
2. source material such as chats, letters, notes, screenshots, or memories
```

我们组装输入：
```
## 关系背景（用户提供）
- 称呼：{name}
- 与用户的关系：{relationship}  
- 用户对他/她的描述：{personality}
- 用户分享的记忆：{extra}
- 上次见面：{last_seen}
- 出生年份/星座MBTI：{birth_info}

## 聊天记录
{chat_log[:30000]}
```

### Step 2: LLM 调用 persona_analyzer.md

使用 `prompts/relationship/persona_analyzer.md` 的完整内容作为 user prompt。

它要求输出格式：
```
Catchphrases: [...]
Frequent wording: [...]
Rhythm: [...]
Warmth level: [...]
Distance style: [...]

Opens up when: [...]
Withdraws when: [...]
Becomes defensive when: [...]
Shows affection when: [...]
Disappears when: [...]

Conflict style: [...]
Defense mechanism: [...]
Repair pattern: [...]
Silence pattern: [...]
Boundary response: [...]

Memorable scenes: [...]
Symbols: [...]
Emotional afterimage: [...]
```

### Step 3: 解析结构化字段

用代码正则解析 Step 2 的输出，提取每个字段的值。未提取到的字段标记为 「证据不足」或使用默认值。

### Step 4: 填入 persona_builder.md 模板

`prompts/relationship/persona_builder.md` 的模板结构有明确的槽位：

```
Layer 0: Core Relational Rules
  - {what they do when they feel close}
  - {what they do when they feel unsafe}
  ...

Layer 2: Expression DNA
  Signature phrases: [...]
  
  > When feeling close:
  > {example}
  
  > When disappointed:
  > {example}
  ...
```

把 Step 3 解析出的字段逐个填入模板对应槽位。

### Step 5: LLM 调用 persona_builder.md

传入已填好的模板，让 LLM 做最终润色和补全。输出即 6 层 persona.md：

```
# {name} — Relationship Persona

## Layer 0: Core Relational Rules
- ...

## Layer 1: Relationship Context
- ...

## Layer 2: Expression DNA
### Signature phrases
- 实际例句1
- 实际例句2

### Example replies
> When feeling close:
> 从聊天记录提取的真实回复

> When disappointed:
> 从聊天记录提取的真实回复

## Layer 3: Emotional Logic
...

## Layer 4: Conflict and Repair
...

## Layer 5: Memory Signature
...

## Correction Log
(empty)
```

---

## 改动范围

| 文件 | 改动 |
|------|------|
| `backend/persona/distiller.py` | 重写 `distill_persona()` 函数 |
| `backend/api/setup.py` | `SetupRequest` 新增 `last_seen`、`birth_info` 字段 |

仅改 2 个文件，前端无变化。

## 预期效果

- persona.md 输出包含真实例句，而非抽象描述
- 6 层结构使 System Prompt 更高效
- LLM 有具体的行为锚点：「生气时用短句」+「例句：算了，你忙吧」
