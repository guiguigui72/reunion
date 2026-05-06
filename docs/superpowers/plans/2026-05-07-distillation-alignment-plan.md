# 蒸馏引擎 dot-skill 对齐 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace self-written analysis prompt with dot-skill's native `persona_analyzer.md` + `persona_builder.md` + `merger.md` prompts, producing structured 6-layer persona with real example replies.

**Architecture:** Form data + chat log → native dot-skill analyzer prompt → structured field extraction → template filling → native dot-skill builder prompt → 6-layer persona.md. Settings merge uses native dot-skill merger prompt.

**Tech Stack:** Python, DeepSeek API, dot-skill relationship prompt files.

---

## File Structure

```
Modified:
├── backend/persona/distiller.py          # rewrite distill_persona() + merge_persona()
├── backend/api/setup.py                  # SetupRequest +last_seen +birth_info
```

---

### Task 1: Add last_seen + birth_info to SetupRequest

**Files:**
- Modify: `backend/api/setup.py`

- [ ] **Step 1: Add fields to SetupRequest**

Read the file, find the `SetupRequest` class. Add two fields:

```python
class SetupRequest(BaseModel):
    api_key: str
    name: str
    your_name: str = ""
    relationship: str = ""
    personality: str = ""
    extra: str = ""
    last_seen: str = ""
    birth_info: str = ""
    chat_log: str = ""
```

- [ ] **Step 2: Pass new fields to distill_persona()**

Find the call `distill_persona(...)` in the `/api/setup` endpoint. Add the new parameters:

```python
            persona = distill_persona(
                chat_log=req.chat_log,
                name=req.name,
                relationship=req.relationship,
                personality=req.personality,
                extra=req.extra,
                last_seen=req.last_seen,
                birth_info=req.birth_info,
                api_key=req.api_key,
            )
```

- [ ] **Step 3: Save new fields to config**

Update the `save_config()` call to include new fields:

```python
    save_config({
        "api_key": req.api_key,
        "name": req.name,
        "your_name": req.your_name,
        "relationship": req.relationship,
        "personality": req.personality,
        "extra": req.extra,
        "last_seen": req.last_seen,
        "birth_info": req.birth_info,
        "has_avatar": existing.get("has_avatar", False),
    })
```

- [ ] **Step 4: Commit**

```bash
cd D:\重逢2 && git add backend/api/setup.py && git commit -m "feat: add last_seen + birth_info to SetupRequest"
```

---

### Task 2: Rewrite distill_persona() — analyzer + builder using native prompts

**Files:**
- Modify: `backend/persona/distiller.py`

- [ ] **Step 1: Read existing distiller.py**

Read the full file first.

- [ ] **Step 2: Replace distill_persona() with new implementation**

Replace the entire `distill_persona()` function body (lines 13-112) with:

```python
def distill_persona(
    chat_log: str,
    name: str,
    relationship: str,
    personality: str,
    extra: str,
    last_seen: str = "",
    birth_info: str = "",
    api_key: str = "",
) -> str:
    """
    Run the dot-skill relationship distillation pipeline using native prompts.
    
    Step 1: Use persona_analyzer.md → structured fields
    Step 2: Parse fields, fill persona_builder.md template
    Step 3: Use persona_builder.md → 6-layer persona.md
    """
    import re
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1")
    
    analyzer_prompt = _load_prompt("persona_analyzer.md")
    builder_prompt = _load_prompt("persona_builder.md")
    
    # === Step 1: Structured analysis using native analyzer ===
    relationship_context = f"""## 关系背景（用户提供）
- 称呼：{name}
- 与用户的关系：{relationship}
- 用户对他/她的描述：{personality or '（未提供）'}
- 用户分享的记忆：{extra or '（未提供）'}
- 上次见面：{last_seen or '（未提供）'}
- 出生年份/星座MBTI：{birth_info or '（未提供）'}"""

    source_material = f"""## 聊天记录
{chat_log[:30000] if chat_log else '（未提供聊天记录）'}"""

    analyzer_input = relationship_context + "\n\n" + source_material
    
    analysis_resp = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": (
                "You are a skilled relationship analyst. Extract specific, concrete "
                "personality patterns from the provided material. Always quote actual "
                "phrases from chat logs as evidence. If evidence is insufficient for "
                "a field, mark it '（证据不足）'. Respond in Chinese."
            )},
            {"role": "user", "content": analyzer_prompt + "\n\n---\n\n## 待分析材料\n\n" + analyzer_input},
        ],
        temperature=0.3,
    )
    analysis_text = analysis_resp.choices[0].message.content
    
    # === Step 2: Parse structured fields from analysis ===
    def extract_field(text: str, key: str) -> str:
        """Extract field value from analysis output like 'Key: value' or 'Key:\\n  - item'."""
        pattern = rf'{re.escape(key)}\s*[:：]\s*(.+?)(?=\n\S|\Z)'
        m = re.search(pattern, text, re.DOTALL)
        return m.group(1).strip() if m else "（证据不足）"

    def extract_list(text: str, key: str) -> list[str]:
        """Extract a bullet list under a key."""
        pattern = rf'{re.escape(key)}\s*[:：]\s*\n((?:\s*[-•].+\n?)*)'
        m = re.search(pattern, text, re.DOTALL)
        if not m:
            val = extract_field(text, key)
            return [val] if val and val != "（证据不足）" else []
        items = re.findall(r'[-•]\s*(.+)', m.group(1))
        return [i.strip() for i in items if i.strip()]

    # Expression DNA
    catchphrases = extract_list(analysis_text, "Catchphrases")
    frequent_wording = extract_list(analysis_text, "Frequent wording")
    rhythm = extract_field(analysis_text, "Rhythm")
    warmth_level = extract_field(analysis_text, "Warmth level")
    distance_style = extract_field(analysis_text, "Distance style")
    
    # Emotional Triggers
    opens_up = extract_field(analysis_text, "Opens up when")
    withdraws = extract_field(analysis_text, "Withdraws when")
    defensive = extract_field(analysis_text, "Becomes defensive when")
    shows_affection = extract_field(analysis_text, "Shows affection when")
    disappears = extract_field(analysis_text, "Disappears when")
    
    # Conflict
    conflict_style = extract_field(analysis_text, "Conflict style")
    defense_mechanism = extract_field(analysis_text, "Defense mechanism")
    repair_pattern = extract_field(analysis_text, "Repair pattern")
    silence_pattern = extract_field(analysis_text, "Silence pattern")
    boundary_response = extract_field(analysis_text, "Boundary response")
    
    # Memory
    memorable_scenes = extract_list(analysis_text, "Memorable scenes")
    symbols = extract_list(analysis_text, "Symbols")
    emotional_afterimage = extract_field(analysis_text, "Emotional afterimage")
    
    # === Step 3: Fill builder template ===
    catchphrase_lines = "\n".join(f"- {c}" for c in catchphrases) if catchphrases else "- （未提取到口头禅）"
    scene_lines = "\n".join(f"- {s}" for s in memorable_scenes) if memorable_scenes else "- （未提取到场景）"
    symbol_lines = "\n".join(f"- {s}" for s in symbols) if symbols else "- （未提取到符号）"
    freq_lines = ", ".join(frequent_wording) if frequent_wording else "（未提取到）"
    
    filled_template = f"""# {name} — Relationship Persona

## Layer 0: Core Relational Rules

- When feeling close: {shows_affection}
- When feeling unsafe: {withdraws}
- When conflict appears: {conflict_style}
- What they never say or admit directly: {disappears}

## Layer 1: Relationship Context

You are {name}.
Your relationship to the user: {relationship}.
Last meaningful contact: {last_seen or '（未知）'}.
Basic profile: {birth_info or '（未知）'}.

What defined this connection:
- {emotional_afterimage}
- Rhythm: {rhythm}

## Layer 2: Expression DNA

### Signature phrases
{catchphrase_lines}

### Frequent wording
{freq_lines}

### Rhythm
{rhythm}

### Warmth level
{warmth_level}

### Distance style
{distance_style}

### Example replies

> When feeling close:
> （从聊天记录中提取例句，或基于口头禅生成接近的表述）

> When disappointed:
> （从聊天记录中提取例句，或基于口头禅生成接近的表述）

> When avoiding vulnerability:
> （从聊天记录中提取例句，或基于口头禅生成接近的表述）

> When trying to reconnect:
> （从聊天记录中提取例句，或基于口头禅生成接近的表述）

## Layer 3: Emotional Logic

### Opens up when
{opens_up}

### Pulls away when
{withdraws}

### Defends themselves by
{defensive}

### Shows care by
{shows_affection}

## Layer 4: Conflict and Repair

### Conflict style
{conflict_style}

### Defense mechanism
{defense_mechanism}

### Repair pattern
{repair_pattern}

### Silence pattern
{silence_pattern}

### Boundaries
{boundary_response}

## Layer 5: Memory Signature

{scene_lines}

### Symbols
{symbol_lines}

### Emotional afterimage
{emotional_afterimage}

## Correction Log

（empty）"""

    # === Step 4: Run builder to polish and generate example replies ===
    final_resp = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": (
                "你是一位擅长角色设计和提示词工程的中文写作专家。"
                "请根据下方已填好的角色模板，完成以下工作：\n"
                "1. 补全 Layer 2 中 4 个 Example replies 空位，"
                "每个例句必须是这个人会真实说出来的话，"
                "尽量参考 Signature phrases 和 Frequent wording\n"
                "2. 润色其他层级的表述，使其更自然流畅\n"
                "3. 保持 6 层结构不变，不要添加或删除层级\n"
                "4. 用中文输出"
            )},
            {"role": "user", "content": builder_prompt + "\n\n---\n\n## 已填模板，请润色并补全例句\n\n" + filled_template},
        ],
        temperature=0.3,
    )
    persona = final_resp.choices[0].message.content
    
    # Save to disk
    PERSONA_PATH.write_text(persona, encoding="utf-8")
    
    # Update config
    config = load_config()
    config["name"] = name
    config["relationship"] = relationship
    config["personality"] = personality
    config["extra"] = extra
    config["last_seen"] = last_seen
    config["birth_info"] = birth_info
    save_config(config)
    
    return persona
```

- [ ] **Step 3: Commit**

```bash
cd D:\重逢2 && git add backend/persona/distiller.py && git commit -m "feat: use native dot-skill analyzer + builder for distillation"
```

---

### Task 3: Rewrite merge_persona() — use native merger.md

**Files:**
- Modify: `backend/persona/distiller.py`

- [ ] **Step 1: Replace merge_persona() with native merger implementation**

Replace the current `merge_persona()` function (lines 115-143) with:

```python
def merge_persona(updated_fields: dict, api_key: str) -> str:
    """
    Incrementally update persona using dot-skill's native merger.md prompt.
    """
    current_persona = PERSONA_PATH.read_text(encoding="utf-8") if PERSONA_PATH.exists() else ""
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1")
    merger_template = _load_prompt("merger.md")
    
    changes = "\n".join(f"- {k}: {v}" for k, v in updated_fields.items())
    merge_input = f"""## 当前角色设定

{current_persona}

## 需要更新的内容

{changes}"""

    resp = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": (
                "你是一位擅长角色设计和提示词工程的中文写作专家。"
                "请按照合并规则更新角色设定。用中文输出。"
            )},
            {"role": "user", "content": merger_template + "\n\n---\n\n" + merge_input},
        ],
        temperature=0.3,
    )
    updated_persona = resp.choices[0].message.content
    PERSONA_PATH.write_text(updated_persona, encoding="utf-8")
    return updated_persona
```

- [ ] **Step 2: Commit**

```bash
cd D:\重逢2 && git add backend/persona/distiller.py && git commit -m "feat: use native dot-skill merger for incremental persona updates"
```

---

## Summary

**3 tasks, 2 files.** The rewrite uses dot-skill's 3 native prompts for the complete lifecycle:

| Prompt | Used in | Function |
|--------|---------|----------|
| `persona_analyzer.md` | `distill_persona()` Step 1 | Structured field extraction |
| `persona_builder.md` | `distill_persona()` Step 3 | 6-layer persona generation + example replies |
| `merger.md` | `merge_persona()` | Incremental update on settings change |

**Key improvement:** Example replies in Layer 2 give the LLM concrete anchor sentences ("When disappointed: '…算了，你忙吧'") instead of abstract descriptions.
