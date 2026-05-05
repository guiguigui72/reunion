from pathlib import Path
from openai import OpenAI

from config import PERSONA_PATH, load_config, save_config

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def _load_prompt(filename: str) -> str:
    return (PROMPTS_DIR / filename).read_text(encoding="utf-8")


def distill_persona(
    chat_log: str,
    name: str,
    relationship: str,
    personality: str,
    extra: str,
    api_key: str,
) -> str:
    """
    Generate a persona system prompt from user input + chat log.

    Uses dot-skill relationship prompts modified for single-pass analysis
    (no interactive Q&A — all info is already available from the form).
    """
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1")

    analysis_prompt = f"""## 任务
你将收到一个人物的基本信息和聊天记录。请基于这些信息，提取这个人的人际模式和表达特征。

## 人物基本信息
- 称呼：{name}
- 与用户的关系：{relationship}
- 用户对他/她的描述：{personality}
- 补充信息：{extra}

## 聊天记录
以下是用户与此人的完整聊天记录（已脱敏处理，仅保留对话内容）：

{chat_log[:30000]}

## 分析要求
请从以下维度分析这个人物：

### 1. 表达 DNA
- 他/她经常使用的词语、句式、语气词
- 句子长度和节奏（短句多还是长句多？）
- 温度：温暖/冷静/热烈/克制？
- 距离感：亲近/疏远/忽冷忽热？
- 在安全和不安时分别怎么说话？

### 2. 情绪触发点
- 什么会让他/她敞开心扉？
- 什么会让他/她变得冷漠或防御？
- 什么会让他/她表现出爱意？
- 什么会让他/她生气或失望？

### 3. 冲突模式
- 他/她如何表达不同意见？
- 是解释、回避、反击、还是沉默？
- 冲突后会主动修复关系吗？
- 他/她如何处理你的负面情绪？

### 4. 记忆印记
- 聊天记录中反复出现的场景或话题
- 他/她对你的特殊称呼
- 经常提到的地点、物品、日常习惯
- 他/她最在意的价值观

## 输出格式
请以第三人称视角，用中文输出一份结构化的「人物角色设定」。
这份设定将被用作 AI 模仿此人的 System Prompt。
请确保每个维度的分析都有聊天记录中的具体例子支持。
如果没有足够信息支撑某个维度，请标注「证据不足」。"""

    analysis_resp = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "你是一位擅长人物分析和角色设计的中文写作专家。你的分析总是具体、细腻、有实际对话支撑。请用中文回复。"},
            {"role": "user", "content": analysis_prompt},
        ],
        temperature=0.3,
    )
    analysis = analysis_resp.choices[0].message.content

    # Step 2: Build persona system prompt from analysis
    builder_template = _load_prompt("persona_builder.md")
    builder_prompt = builder_template + "\n\n---\n\n## 人物分析\n\n" + analysis

    builder_resp = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "你是一位擅长角色设计和提示词工程的中文写作专家。请用中文生成角色 System Prompt。"},
            {"role": "user", "content": builder_prompt},
        ],
        temperature=0.3,
    )
    persona = builder_resp.choices[0].message.content

    # Save to disk
    PERSONA_PATH.write_text(persona, encoding="utf-8")

    # Update config
    config = load_config()
    config["name"] = name
    config["relationship"] = relationship
    config["personality"] = personality
    config["extra"] = extra
    save_config(config)

    return persona


def merge_persona(updated_fields: dict, api_key: str) -> str:
    """
    Incrementally update persona when user changes settings.
    """
    current_persona = PERSONA_PATH.read_text(encoding="utf-8") if PERSONA_PATH.exists() else ""
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1")

    changes = "\n".join(f"- {k}: {v}" for k, v in updated_fields.items())
    prompt = f"""## 当前角色设定

{current_persona}

## 需要更新的内容

{changes}

请更新以上角色设定，只修改受影响的部分，保留其他内容不变。输出完整的更新后设定。"""

    resp = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "你是一位擅长角色设计的专家。请用中文回复。"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
    )
    updated_persona = resp.choices[0].message.content
    PERSONA_PATH.write_text(updated_persona, encoding="utf-8")
    return updated_persona


def extract_entities(chat_log: str, api_key: str) -> list[dict]:
    """
    Scan chat log for entities the LLM doesn't fully understand.
    Returns a list of question objects for the smart follow-up step.
    """
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1")

    prompt = f"""## 任务
扫描以下聊天记录，找出其中频繁出现但上下文不够明确的实体。
这些实体可能是：
- pet: 宠物（名字、品种不明）
- person: 人物（身份、与用户的关系不明）
- place: 地点（具体位置、意义不明）
- object: 物品/事物（具体指代不明）
- generic: 其他值得确认的概念

## 要求
1. 只返回确实需要确认的实体（2-5个），不要编造
2. 用JSON数组格式返回，每个元素包含：
   - entity: 实体的名称（聊天记录中的原始称呼）
   - context: 在聊天记录中出现的上下文（简短引用）
   - type: 实体类型（pet/person/place/object/generic）
   - context_hint: 一句话的引导问题（中文，口语化）
3. 如果聊天记录为空或没有不确定的实体，返回空数组 []

## 聊天记录
{chat_log[:15000]}

## 输出格式（仅输出JSON数组，不要其他内容）
[
  {{
    "entity": "球球",
    "context": "你妈妈说'球球今天又不吃饭了'",
    "type": "pet",
    "context_hint": "球球是你们养的宠物吗？"
  }}
]"""

    resp = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "你是一个实体识别助手。只输出JSON数组，不输出其他内容。"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.0,
        max_tokens=1024,
    )
    raw = resp.choices[0].message.content.strip()
    # Parse JSON, handling markdown code blocks
    import json
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0]
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return []


def merge_answers(answers: list[dict], api_key: str) -> str:
    """
    Merge user's answers to smart follow-up questions into the persona.

    answers: [{"entity": "球球", "type": "pet", "detail": "金毛犬，养了6年", "context_hint": "球球是你们养的宠物吗？"}]
    """
    current_persona = PERSONA_PATH.read_text(encoding="utf-8") if PERSONA_PATH.exists() else ""
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1")

    answers_text = "\n".join(
        f"- {a['entity']}（{a.get('type', '未知')}）：{a.get('detail', '无补充')}（上下文：{a.get('context_hint', '')}）"
        for a in answers
    )

    prompt = f"""## 当前角色设定

{current_persona}

## 新增背景信息

以下是在聊天记录中发现的实体，用户已补充了说明：

{answers_text}

请将这些信息自然地融入角色设定中。保留原有内容不变，只追加和补充这些实体的背景。
输出完整的更新后角色设定。"""

    resp = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "你是一位擅长角色设计的专家。请用中文回复。"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
    )
    updated = resp.choices[0].message.content
    PERSONA_PATH.write_text(updated, encoding="utf-8")
    return updated
