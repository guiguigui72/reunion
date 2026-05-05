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
