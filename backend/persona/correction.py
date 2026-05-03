from pathlib import Path
from openai import OpenAI

from config import PERSONA_PATH

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def handle_correction(user_message: str, api_key: str) -> str:
    """
    Detect if user is correcting the persona, extract the correction,
    update persona, and return an in-character response.

    Returns: response in character
    """
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1")

    current_persona = PERSONA_PATH.read_text(encoding="utf-8") if PERSONA_PATH.exists() else ""
    correction_prompt = (PROMPTS_DIR / "correction_handler.md").read_text(encoding="utf-8")

    full_prompt = correction_prompt.replace("{{persona}}", current_persona)
    full_prompt = full_prompt.replace("{{user_message}}", user_message)

    resp = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": (
                "You are the AI persona. Respond IN CHARACTER, in Chinese. "
                "If the user corrects you, acknowledge naturally (e.g. '啊…是我记错了', "
                "'你说得对，太久没见了脑子有点乱'), then correct yourself. "
                "NEVER break character. NEVER speak as a system or assistant. "
                "Stay in the persona's voice at all times."
            )},
            {"role": "user", "content": full_prompt},
        ],
        temperature=0.7,
    )
    response = resp.choices[0].message.content

    return response


def is_correction_intent(message: str) -> bool:
    """
    Lightweight check: does this message look like the user
    is correcting the AI's behavior/personality?
    """
    keywords = [
        "你不会", "他才不会", "她才不会", "他不会",
        "不像你", "不像他", "不像她",
        "你不是这样", "他不会这样", "她不会这样",
        "说错了", "记错了", "不对",
        "你什么时候", "你以前",
        "这不是你", "这不是他",
    ]
    msg = message.strip().lower()
    return any(kw in msg for kw in keywords)
