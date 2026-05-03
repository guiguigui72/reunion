import re
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
    Run the dot-skill relationship distillation pipeline.

    1. intake -> structure the raw inputs
    2. persona_analyzer -> extract 4 dimensions
    3. persona_builder -> generate final system prompt

    Returns the persona system prompt as a markdown string.
    """
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1")

    intake_template = _load_prompt("intake.md")
    analyzer_template = _load_prompt("persona_analyzer.md")
    builder_template = _load_prompt("persona_builder.md")

    # Step 1: Intake - structure inputs
    intake_prompt = intake_template.replace("{{name}}", name)
    intake_prompt = intake_prompt.replace("{{relationship}}", relationship)
    intake_prompt = intake_prompt.replace("{{personality}}", personality)
    intake_prompt = intake_prompt.replace("{{extra}}", extra)
    intake_prompt = intake_prompt.replace("{{chat_log}}", chat_log[:30000])

    intake_resp = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "You are a skilled relationship analyst. Respond in Chinese."},
            {"role": "user", "content": intake_prompt},
        ],
        temperature=0.3,
    )
    structured_input = intake_resp.choices[0].message.content

    # Step 2: Analyze - extract 4 dimensions
    analysis_resp = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "You are a skilled relationship analyst. Respond in Chinese."},
            {"role": "user", "content": analyzer_template + "\n\n---\n\n## Input\n\n" + structured_input},
        ],
        temperature=0.3,
    )
    analysis = analysis_resp.choices[0].message.content

    # Step 3: Build - generate final persona prompt
    builder_resp = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "You are a skilled character designer. Respond in Chinese."},
            {"role": "user", "content": builder_template + "\n\n---\n\n## Analysis\n\n" + analysis},
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
    Uses dot-skill merger.md prompt.
    """
    current_persona = PERSONA_PATH.read_text(encoding="utf-8") if PERSONA_PATH.exists() else ""
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1")
    merger_template = _load_prompt("merger.md")

    changes = "\n".join(f"- {k}: {v}" for k, v in updated_fields.items())
    prompt = merger_template.replace("{{current_persona}}", current_persona)
    prompt = prompt.replace("{{changes}}", changes)

    resp = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "You are a skilled character designer. Respond in Chinese."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
    )
    updated_persona = resp.choices[0].message.content
    PERSONA_PATH.write_text(updated_persona, encoding="utf-8")
    return updated_persona
