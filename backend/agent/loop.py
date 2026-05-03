from openai import OpenAI

from config import PERSONA_PATH, load_config
from rag.embedder import embed_texts
from rag.store import query_collection
from persona.correction import handle_correction, is_correction_intent

GUARDRAIL = """
## 重要规则
- 只依据下方「记忆片段」中的内容回答。
- 如果记忆片段中没有相关信息，请坦诚地说「记不太清了」或「我好像想不起来了」。
- 绝不编造不存在的记忆或经历。
- 用自然、口语化的方式回应，就像日常聊天一样。
"""


def build_system_prompt(persona: str, memories: list[str]) -> str:
    memory_text = "\n".join(f"- {m}" for m in memories) if memories else "（暂无相关记忆）"
    return f"{persona}\n\n{GUARDRAIL}\n\n## 记忆片段\n{memory_text}"


def classify_intent(user_message: str, api_key: str) -> dict:
    """
    Use LLM to decide: is this a correction, a regular message,
    or something that needs memory search?

    Returns: {"type": "correction"|"chat"|"memory_search", "query": str|None}
    """
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1")

    resp = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": (
                "Classify this user message in a chat with their AI companion "
                "that mimics a deceased loved one. Reply with ONLY one word:\n"
                "- 'correction' if user is saying the AI doesn't sound like the person\n"
                "- 'memory_search' if the message asks about past events/memories\n"
                "- 'chat' if it's casual conversation (greetings, feelings, daily chat)\n\n"
                "Examples:\n"
                "'他才不会这么说' -> correction\n"
                "'你还记得我们去海边那次吗' -> memory_search\n"
                "'今天好累啊' -> chat"
            )},
            {"role": "user", "content": user_message},
        ],
        max_tokens=10,
        temperature=0.0,
    )
    result = resp.choices[0].message.content.strip().lower()

    query = None
    intent_type = "chat"
    if "correction" in result:
        intent_type = "correction"
    elif "memory" in result:
        intent_type = "memory_search"
        query = user_message

    return {"type": intent_type, "query": query}


def chat(user_message: str, api_key: str) -> str:
    """
    Main agent loop entry point.

    1. Check for correction intent
    2. If normal: decide memory search needed? -> search -> build prompt -> reply
    """
    config = load_config()

    # Check correction
    if is_correction_intent(user_message):
        return handle_correction(user_message, api_key)

    # Classify intent via LLM
    intent = classify_intent(user_message, api_key)

    if intent["type"] == "correction":
        return handle_correction(user_message, api_key)

    # Load persona
    persona = ""
    if PERSONA_PATH.exists():
        persona = PERSONA_PATH.read_text(encoding="utf-8")

    # Memory search
    memories = []
    if intent["type"] == "memory_search":
        query_embedding = embed_texts([user_message])[0]
        memories = query_collection(query_embedding, n_results=5)

    # Build prompt and call LLM
    system_prompt = build_system_prompt(persona, memories)

    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1")

    resp = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=0.7,
        max_tokens=1024,
    )

    return resp.choices[0].message.content
