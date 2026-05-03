# 重逢 MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a desktop app that lets users import chat logs of a deceased loved one and chat with an AI that mimics them, using local RAG + personality distillation.

**Architecture:** Electron desktop shell spawns a Python FastAPI subprocess. React frontend communicates with Python via localhost HTTP. Python handles LangChain chunking, BGE embeddings, ChromaDB retrieval, dot-skill personality distillation, ReAct agent loop, and DeepSeek API calls.

**Tech Stack:** Electron, React (TypeScript, Vite), Python (FastAPI, ChromaDB, sentence-transformers, LangChain), SQLite, DeepSeek API. Target: Windows MVP.

---

## File Structure

```
reunion/
├── package.json
├── tsconfig.json
├── vite.config.ts
├── electron/
│   ├── main.js
│   └── preload.js
├── src/
│   ├── index.html
│   ├── index.tsx
│   ├── App.tsx
│   ├── App.css
│   ├── api.ts
│   ├── types.ts
│   ├── components/
│   │   ├── Wizard.tsx
│   │   ├── ChatWindow.tsx
│   │   ├── MessageBubble.tsx
│   │   ├── SettingsPanel.tsx
│   │   └── DeleteConfirm.tsx
│   └── hooks/
│       ├── useChat.ts
│       └── useSetup.ts
├── backend/
│   ├── requirements.txt
│   ├── main.py
│   ├── config.py
│   ├── prompts/          (5 dot-skill .md files)
│   ├── rag/
│   │   ├── __init__.py
│   │   ├── chunker.py
│   │   ├── embedder.py
│   │   └── store.py
│   ├── persona/
│   │   ├── __init__.py
│   │   ├── distiller.py
│   │   └── correction.py
│   ├── agent/
│   │   ├── __init__.py
│   │   └── loop.py
│   ├── chat/
│   │   ├── __init__.py
│   │   └── history.py
│   └── api/
│       ├── __init__.py
│       ├── setup.py
│       ├── chat.py
│       └── settings.py
├── .gitignore
└── README.md
```

---

### Task 1: Project scaffolding

**Files:**
- Create: `package.json`
- Create: `tsconfig.json`
- Create: `vite.config.ts`
- Create: `src/index.html`
- Create: `.gitignore` (update)
- Create: `backend/requirements.txt`
- Create: `backend/__init__.py`
- Create: `backend/rag/__init__.py`
- Create: `backend/persona/__init__.py`
- Create: `backend/agent/__init__.py`
- Create: `backend/chat/__init__.py`
- Create: `backend/api/__init__.py`
- Create: `README.md`

- [ ] **Step 1: Create package.json**

```json
{
  "name": "reunion",
  "version": "0.1.0",
  "description": "重逢 — AI companion for remembering loved ones",
  "main": "electron/main.js",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "electron:dev": "concurrently \"vite\" \"wait-on http://localhost:5173 && electron .\"",
    "electron:build": "vite build && electron-builder"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1"
  },
  "devDependencies": {
    "@types/react": "^18.3.12",
    "@types/react-dom": "^18.3.1",
    "@vitejs/plugin-react": "^4.3.4",
    "concurrently": "^9.1.0",
    "electron": "^33.2.0",
    "typescript": "^5.6.3",
    "vite": "^6.0.3",
    "wait-on": "^8.0.1"
  }
}
```

- [ ] **Step 2: Create tsconfig.json**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "jsx": "react-jsx",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "outDir": "dist",
    "rootDir": "src"
  },
  "include": ["src"]
}
```

- [ ] **Step 3: Create vite.config.ts**

```typescript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  base: './',
  build: {
    outDir: 'dist/renderer',
  },
  server: {
    port: 5173,
  },
});
```

- [ ] **Step 4: Create src/index.html**

```html
<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>重逢</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="./index.tsx"></script>
  </body>
</html>
```

- [ ] **Step 5: Update .gitignore**

```
node_modules/
dist/
__pycache__/
*.pyc
.env
.superpowers/
chroma/
*.db
*.log
```

- [ ] **Step 6: Create backend/requirements.txt**

```
fastapi==0.115.6
uvicorn==0.34.0
langchain==0.3.13
langchain-text-splitters==0.3.2
chromadb==0.5.23
sentence-transformers==3.3.1
openai==1.57.2
pydantic==2.10.4
```

- [ ] **Step 7: Create empty __init__.py files**

```bash
New-Item -Path "backend/rag/__init__.py" -ItemType File
New-Item -Path "backend/persona/__init__.py" -ItemType File
New-Item -Path "backend/agent/__init__.py" -ItemType File
New-Item -Path "backend/chat/__init__.py" -ItemType File
New-Item -Path "backend/api/__init__.py" -ItemType File
```

- [ ] **Step 8: Install dependencies**

```bash
npm install
```

- [ ] **Step 9: Commit**

```bash
git add -A
git commit -m "chore: project scaffolding - Electron + React + Python backend"
```

---

### Task 2: Python config management

**Files:**
- Create: `backend/config.py`

- [ ] **Step 1: Write config.py**

```python
import json
import os
from pathlib import Path

DATA_DIR = Path.home() / ".reunion"
CONFIG_PATH = DATA_DIR / "config.json"
PERSONA_PATH = DATA_DIR / "persona.md"
AVATAR_PATH = DATA_DIR / "avatar.png"


def ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> dict:
    ensure_data_dir()
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return {}


def save_config(config: dict) -> None:
    ensure_data_dir()
    CONFIG_PATH.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")


def is_configured() -> bool:
    """Return True if the user has completed initial setup."""
    config = load_config()
    return bool(config.get("api_key") and config.get("name") and config.get("persona"))
```

- [ ] **Step 2: Verify it loads (quick smoke test)**

```bash
cd backend && python -c "from config import load_config, save_config; save_config({'test': True}); print(load_config())"
```
Expected: `{'test': True}`

- [ ] **Step 3: Commit**

```bash
git add backend/config.py
git commit -m "feat: config management for ~/.reunion/"
```

---

### Task 3: Chat history (SQLite)

**Files:**
- Create: `backend/chat/history.py`

- [ ] **Step 1: Write history.py**

```python
import sqlite3
from datetime import datetime

from config import DATA_DIR, ensure_data_dir

DB_PATH = DATA_DIR / "chat_history.db"


def get_conn() -> sqlite3.Connection:
    ensure_data_dir()
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
            content TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    conn.close()


def save_message(role: str, content: str) -> None:
    conn = get_conn()
    conn.execute(
        "INSERT INTO messages (role, content) VALUES (?, ?)",
        (role, content),
    )
    conn.commit()
    conn.close()


def get_history(limit: int = 50) -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT role, content FROM messages ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [{"role": r[0], "content": r[1]} for r in reversed(rows)]


def clear_history() -> None:
    conn = get_conn()
    conn.execute("DELETE FROM messages")
    conn.commit()
    conn.close()


init_db()
```

- [ ] **Step 2: Smoke test**

```bash
cd backend && python -c "
from chat.history import save_message, get_history, clear_history
save_message('user', 'hello')
save_message('assistant', 'hi there')
msgs = get_history()
assert len(msgs) == 2
assert msgs[0]['role'] == 'user'
clear_history()
assert len(get_history()) == 0
print('PASS')
"
```

- [ ] **Step 3: Commit**

```bash
git add backend/chat/history.py backend/chat/__init__.py
git commit -m "feat: SQLite chat history"
```

---

### Task 4: RAG engine (chunker + embedder + ChromaDB store)

**Files:**
- Create: `backend/rag/chunker.py`
- Create: `backend/rag/embedder.py`
- Create: `backend/rag/store.py`

- [ ] **Step 1: Write chunker.py**

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter


def chunk_text(text: str, chunk_size: int = 512, overlap: int = 64) -> list[str]:
    """
    Split raw chat log into overlapping chunks.
    For chat logs, preserve line structure where possible.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap,
        separators=["\n\n", "\n", "。", ".", "！", "!", "？", "?", " ", ""],
    )
    return splitter.split_text(text)


def parse_chat_log(raw_text: str) -> list[str]:
    """
    Parse a WeChat/QQ-style chat log and extract only the
    deceased person's messages for RAG indexing.
    
    Expected format (WeChat export):
    2024-01-01 12:00 用户名
    message text
    
    Returns only the messages where sender matches target_name.
    We extract all messages (both sides) for distillation,
    but only the target's messages for RAG.
    """
    import re
    lines = raw_text.split("\n")
    messages = []
    current_sender = None
    current_msg = []
    
    header_pattern = re.compile(
        r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}\s+\d{1,2}:\d{2}(?::\d{2})?\s+(.+)"
    )
    
    for line in lines:
        m = header_pattern.match(line.strip())
        if m:
            if current_msg and current_sender:
                messages.append({
                    "sender": current_sender.strip(),
                    "content": "\n".join(current_msg).strip(),
                })
            current_sender = m.group(1)
            current_msg = []
        else:
            if line.strip():
                current_msg.append(line.strip())
    
    if current_msg and current_sender:
        messages.append({
            "sender": current_sender.strip(),
            "content": "\n".join(current_msg).strip(),
        })
    
    return messages


def extract_target_only(raw_text: str, target_name: str) -> str:
    """
    Extract only the target person's messages, concatenated
    as a single text for embedding.
    """
    all_msgs = parse_chat_log(raw_text)
    target_msgs = [m["content"] for m in all_msgs if m["sender"] == target_name]
    return "\n\n".join(target_msgs)
```

- [ ] **Step 2: Write embedder.py**

```python
from sentence_transformers import SentenceTransformer

MODEL_NAME = "BAAI/bge-small-zh-v1.5"

_embedder: SentenceTransformer | None = None


def get_embedder() -> SentenceTransformer:
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer(MODEL_NAME)
    return _embedder


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a list of text chunks."""
    model = get_embedder()
    embeddings = model.encode(texts, normalize_embeddings=True)
    return embeddings.tolist()
```

- [ ] **Step 3: Write store.py**

```python
import chromadb
from chromadb.config import Settings

from config import DATA_DIR, ensure_data_dir

CHROMA_DIR = str(DATA_DIR / "chroma")

_client: chromadb.PersistentClient | None = None


def get_client() -> chromadb.PersistentClient:
    global _client
    if _client is None:
        ensure_data_dir()
        _client = chromadb.PersistentClient(
            path=CHROMA_DIR,
            settings=Settings(anonymized_telemetry=False),
        )
    return _client


def get_or_create_collection(name: str = "memories"):
    client = get_client()
    existing = [c.name for c in client.list_collections()]
    if name in existing:
        client.delete_collection(name)
    return client.create_collection(name=name, metadata={"hnsw:space": "cosine"})


def query_collection(query_embedding: list[float], n_results: int = 5):
    client = get_client()
    try:
        col = client.get_collection("memories")
    except Exception:
        return []
    results = col.query(query_embeddings=[query_embedding], n_results=n_results)
    return results["documents"][0] if results["documents"] else []
```

- [ ] **Step 4: Smoke test chunker**

```bash
cd backend && python -c "
from rag.chunker import chunk_text, parse_chat_log
sample = '2024-01-01 12:00 妈妈\n吃饭了没\n\n2024-01-01 12:01 我\n还没呢\n'
msgs = parse_chat_log(sample)
assert len(msgs) == 2
assert msgs[0]['sender'] == '妈妈'
chunks = chunk_text('你好。今天天气不错。出去走走吧。')
assert len(chunks) > 0
print('PASS')
"
```

- [ ] **Step 5: Commit**

```bash
git add backend/rag/
git commit -m "feat: RAG engine - chunker, BGE embedder, ChromaDB store"
```

---

### Task 5: Embed dot-skill prompts + persona distiller

**Files:**
- Create: `backend/prompts/intake.md`
- Create: `backend/prompts/persona_analyzer.md`
- Create: `backend/prompts/persona_builder.md`
- Create: `backend/prompts/merger.md`
- Create: `backend/prompts/correction_handler.md`
- Create: `backend/persona/distiller.py`

- [ ] **Step 1: Fetch and save dot-skill relationship prompts**

```bash
curl -sL "https://raw.githubusercontent.com/titanwings/colleague-skill/dot-skill/prompts/relationship/intake.md" -o backend/prompts/intake.md
curl -sL "https://raw.githubusercontent.com/titanwings/colleague-skill/dot-skill/prompts/relationship/persona_analyzer.md" -o backend/prompts/persona_analyzer.md
curl -sL "https://raw.githubusercontent.com/titanwings/colleague-skill/dot-skill/prompts/relationship/persona_builder.md" -o backend/prompts/persona_builder.md
curl -sL "https://raw.githubusercontent.com/titanwings/colleague-skill/dot-skill/prompts/relationship/merger.md" -o backend/prompts/merger.md
curl -sL "https://raw.githubusercontent.com/titanwings/colleague-skill/dot-skill/prompts/correction_handler.md" -o backend/prompts/correction_handler.md
```

- [ ] **Step 2: Write persona/distiller.py**

```python
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
```

- [ ] **Step 3: Commit**

```bash
git add backend/prompts/ backend/persona/distiller.py
git commit -m "feat: embed dot-skill relationship prompts + persona distiller"
```

---

### Task 6: Agent loop + correction detection

**Files:**
- Create: `backend/agent/loop.py`
- Create: `backend/persona/correction.py`

- [ ] **Step 1: Write persona/correction.py**

```python
from pathlib import Path
from openai import OpenAI

from config import PERSONA_PATH

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def handle_correction(user_message: str, api_key: str) -> str:
    """
    Detect if user is correcting the persona, extract the correction,
    update persona, and return an in-character response.
    
    Returns: (correction_applied: bool, response: str)
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
```

- [ ] **Step 2: Write agent/loop.py**

```python
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
    3. Save to history (caller handles this)
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
```

- [ ] **Step 3: Commit**

```bash
git add backend/persona/correction.py backend/agent/loop.py
git commit -m "feat: agent loop with ReAct + correction detection"
```

---

### Task 7: FastAPI endpoints (setup, chat, settings)

**Files:**
- Create: `backend/api/setup.py`
- Create: `backend/api/chat.py`
- Create: `backend/api/settings.py`
- Create: `backend/main.py`

- [ ] **Step 1: Write api/setup.py**

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from config import save_config, load_config
from rag.chunker import chunk_text, extract_target_only
from rag.embedder import embed_texts
from rag.store import get_or_create_collection
from persona.distiller import distill_persona

router = APIRouter()


class SetupRequest(BaseModel):
    api_key: str
    name: str
    your_name: str = ""
    relationship: str = ""
    personality: str = ""
    extra: str = ""
    chat_log: str = ""


@router.post("/api/setup")
async def setup(req: SetupRequest):
    if not req.api_key or not req.name:
        raise HTTPException(status_code=400, detail="api_key and name are required")

    # Save config first
    save_config({
        "api_key": req.api_key,
        "name": req.name,
        "your_name": req.your_name,
        "relationship": req.relationship,
        "personality": req.personality,
        "extra": req.extra,
    })

    # Distill persona
    persona = ""
    if req.chat_log.strip():
        try:
            persona = distill_persona(
                chat_log=req.chat_log,
                name=req.name,
                relationship=req.relationship,
                personality=req.personality,
                extra=req.extra,
                api_key=req.api_key,
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"人格蒸馏失败: {str(e)}")

        # Chunk and embed target's messages
        try:
            target_text = extract_target_only(req.chat_log, req.name)
            if target_text.strip():
                chunks = chunk_text(target_text)
                embeddings = embed_texts(chunks)
                collection = get_or_create_collection("memories")
                collection.add(
                    documents=chunks,
                    embeddings=embeddings,
                    ids=[f"mem_{i}" for i in range(len(chunks))],
                )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"记忆索引失败: {str(e)}")

    return {
        "status": "ok",
        "message": "设置完成",
        "has_persona": bool(persona),
    }
```

- [ ] **Step 2: Write api/chat.py**

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from config import load_config
from agent.loop import chat as agent_chat
from chat.history import save_message, get_history

router = APIRouter()


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str
    history: list[dict]


@router.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    config = load_config()
    api_key = config.get("api_key", "")
    if not api_key:
        raise HTTPException(status_code=400, detail="请先设置 API Key")

    if not req.message.strip():
        raise HTTPException(status_code=400, detail="消息不能为空")

    save_message("user", req.message)

    try:
        reply = agent_chat(req.message, api_key)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"对话失败: {str(e)}")

    save_message("assistant", reply)

    return ChatResponse(
        reply=reply,
        history=get_history(50),
    )


@router.get("/api/chat/history")
async def chat_history():
    return {"history": get_history(50)}
```

- [ ] **Step 3: Write api/settings.py**

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from config import load_config, save_config, PERSONA_PATH
from persona.distiller import merge_persona

router = APIRouter()


class SettingsUpdate(BaseModel):
    api_key: str = ""
    name: str = ""
    your_name: str = ""
    relationship: str = ""
    personality: str = ""
    extra: str = ""


@router.get("/api/settings")
async def get_settings():
    config = load_config()
    return {
        "api_key": config.get("api_key", "")[:8] + "****" if config.get("api_key") else "",
        "name": config.get("name", ""),
        "your_name": config.get("your_name", ""),
        "relationship": config.get("relationship", ""),
        "personality": config.get("personality", ""),
        "extra": config.get("extra", ""),
        "has_avatar": config.get("has_avatar", False),
    }


@router.put("/api/settings")
async def update_settings(req: SettingsUpdate):
    config = load_config()
    api_key = req.api_key if req.api_key and "****" not in req.api_key else config.get("api_key", "")

    updated = {}
    if req.name and req.name != config.get("name"):
        updated["name"] = req.name
    if req.personality and req.personality != config.get("personality"):
        updated["personality"] = req.personality
    if req.extra != config.get("extra"):
        updated["extra"] = req.extra
    if req.relationship and req.relationship != config.get("relationship"):
        updated["relationship"] = req.relationship

    new_config = {
        "api_key": api_key,
        "name": req.name or config.get("name", ""),
        "your_name": req.your_name or config.get("your_name", ""),
        "relationship": req.relationship or config.get("relationship", ""),
        "personality": req.personality or config.get("personality", ""),
        "extra": req.extra or config.get("extra", ""),
    }
    save_config(new_config)

    if updated and PERSONA_PATH.exists() and api_key:
        try:
            merge_persona(updated, api_key)
        except Exception:
            pass

    return {"status": "ok"}


@router.delete("/api/settings/reset")
async def reset_all():
    import shutil
    from config import DATA_DIR
    if DATA_DIR.exists():
        shutil.rmtree(str(DATA_DIR))
    return {"status": "ok", "message": "已清除所有数据"}
```

- [ ] **Step 4: Write main.py**

```python
import sys
import socket
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from api.setup import router as setup_router
from api.chat import router as chat_router
from api.settings import router as settings_router

app = FastAPI(title="重逢 Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(setup_router)
app.include_router(chat_router)
app.include_router(settings_router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


def find_free_port() -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def main():
    port_file_path = sys.argv[1] if len(sys.argv) > 1 else None

    port = find_free_port()

    if port_file_path:
        pf = Path(port_file_path)
        pf.parent.mkdir(parents=True, exist_ok=True)
        pf.write_text(str(port))
        print(f"Port {port} written to {port_file_path}", flush=True)

    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Test health endpoint**

```bash
cd backend && Start-Process -NoNewWindow python -ArgumentList "main.py", "$env:TEMP\reunion_port.txt"
Start-Sleep -Seconds 3
$port = Get-Content "$env:TEMP\reunion_port.txt"
$response = Invoke-RestMethod -Uri "http://127.0.0.1:$port/api/health" -Method Get
$response.status
# Expected: "ok"
Stop-Process -Name python -Force
```

- [ ] **Step 6: Commit**

```bash
git add backend/api/ backend/main.py
git commit -m "feat: FastAPI endpoints - setup, chat, settings, health"
```

---

### Task 8: Electron main process

**Files:**
- Create: `electron/main.js`
- Create: `electron/preload.js`

- [ ] **Step 1: Write electron/main.js**

```javascript
const { app, BrowserWindow } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const os = require('os');

let mainWindow = null;
let pythonProcess = null;
const PORT_FILE = path.join(os.tmpdir(), 'reunion_port.txt');

function getPythonCommand() {
    // Try python3 first, then python
    return process.platform === 'win32' ? 'python' : 'python3';
}

function startPythonBackend() {
    // Clean up old port file
    try { fs.unlinkSync(PORT_FILE); } catch (_) {}

    const backendDir = path.join(__dirname, '..', 'backend');
    
    pythonProcess = spawn(getPythonCommand(), ['main.py', PORT_FILE], {
        cwd: backendDir,
        stdio: ['pipe', 'pipe', 'pipe'],
    });

    pythonProcess.stdout.on('data', (data) => {
        console.log(`[Python] ${data.toString().trim()}`);
    });

    pythonProcess.stderr.on('data', (data) => {
        console.error(`[Python Error] ${data.toString().trim()}`);
    });

    pythonProcess.on('close', (code) => {
        console.log(`[Python] Process exited with code ${code}`);
    });
}

function waitForPort(maxRetries = 30, interval = 1000) {
    return new Promise((resolve, reject) => {
        let retries = 0;
        const check = () => {
            try {
                const port = fs.readFileSync(PORT_FILE, 'utf-8').trim();
                if (port && !isNaN(parseInt(port))) {
                    resolve(parseInt(port));
                    return;
                }
            } catch (_) {}
            
            retries++;
            if (retries >= maxRetries) {
                reject(new Error('Python backend did not start in time'));
                return;
            }
            setTimeout(check, interval);
        };
        check();
    });
}

async function createWindow() {
    const port = await waitForPort();

    mainWindow = new BrowserWindow({
        width: 420,
        height: 720,
        minWidth: 360,
        minHeight: 500,
        title: '重逢',
        webPreferences: {
            preload: path.join(__dirname, 'preload.js'),
            contextIsolation: true,
            nodeIntegration: false,
        },
        // Warm, soft look
        backgroundColor: '#faf8f5',
        titleBarStyle: 'default',
    });

    // Pass backend port to renderer
    mainWindow.webContents.on('did-finish-load', () => {
        mainWindow.webContents.send('backend-port', port);
    });

    // In dev mode, load Vite dev server
    const isDev = process.argv.includes('--dev') || process.env.NODE_ENV === 'development';
    if (isDev) {
        mainWindow.loadURL('http://localhost:5173');
    } else {
        mainWindow.loadFile(path.join(__dirname, '..', 'dist', 'renderer', 'index.html'));
    }
}

app.whenReady().then(() => {
    startPythonBackend();
    createWindow();
});

app.on('window-all-closed', () => {
    if (pythonProcess) {
        pythonProcess.kill();
    }
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

app.on('before-quit', () => {
    if (pythonProcess) {
        pythonProcess.kill();
    }
});
```

- [ ] **Step 2: Write electron/preload.js**

```javascript
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
    getBackendPort: () => {
        return new Promise((resolve) => {
            ipcRenderer.once('backend-port', (_event, port) => {
                resolve(port);
            });
        });
    },
});
```

Wait — the main process uses `webContents.send` but the preload needs `ipcRenderer.on`. Let's fix: `webContents.send` in main pairs with `ipcRenderer.on` in preload. Actually, `webContents.send` sends to the renderer process, and in the preload we listen with `ipcRenderer.on`. But `webContents.send` fires only if the listener is already registered. Since we call `send` on `did-finish-load`, the preload script has already run, so this should work.

However, there's a subtlety: `ipcRenderer.once` might miss the message if it fires before the renderer calls `getBackendPort()`. Let's use a different approach — store the port and use `ipcRenderer.invoke` / `ipcMain.handle`:

Updated main.js:

```javascript
const { app, BrowserWindow, ipcMain } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const os = require('os');

let mainWindow = null;
let pythonProcess = null;
let backendPort = null;
const PORT_FILE = path.join(os.tmpdir(), 'reunion_port.txt');

function getPythonCommand() {
    return process.platform === 'win32' ? 'python' : 'python3';
}

function startPythonBackend() {
    try { fs.unlinkSync(PORT_FILE); } catch (_) {}

    const backendDir = path.join(__dirname, '..', 'backend');

    pythonProcess = spawn(getPythonCommand(), ['main.py', PORT_FILE], {
        cwd: backendDir,
        stdio: ['pipe', 'pipe', 'pipe'],
    });

    pythonProcess.stdout.on('data', (data) => {
        console.log(`[Python] ${data.toString().trim()}`);
    });

    pythonProcess.stderr.on('data', (data) => {
        console.error(`[Python Error] ${data.toString().trim()}`);
    });
}

function waitForPort(maxRetries = 30, interval = 1000) {
    return new Promise((resolve, reject) => {
        let retries = 0;
        const check = () => {
            try {
                const port = fs.readFileSync(PORT_FILE, 'utf-8').trim();
                if (port && !isNaN(parseInt(port))) {
                    resolve(parseInt(port));
                    return;
                }
            } catch (_) {}
            retries++;
            if (retries >= maxRetries) {
                reject(new Error('Python backend did not start in time'));
                return;
            }
            setTimeout(check, interval);
        };
        check();
    });
}

async function createWindow() {
    backendPort = await waitForPort();

    mainWindow = new BrowserWindow({
        width: 420,
        height: 720,
        minWidth: 360,
        minHeight: 500,
        title: '重逢',
        webPreferences: {
            preload: path.join(__dirname, 'preload.js'),
            contextIsolation: true,
            nodeIntegration: false,
        },
        backgroundColor: '#faf8f5',
    });

    const isDev = process.argv.includes('--dev');
    if (isDev) {
        mainWindow.loadURL('http://localhost:5173');
    } else {
        mainWindow.loadFile(path.join(__dirname, '..', 'dist', 'renderer', 'index.html'));
    }
}

// IPC handler: renderer asks for backend port
ipcMain.handle('get-backend-port', () => backendPort);

app.whenReady().then(() => {
    startPythonBackend();
    createWindow();
});

app.on('window-all-closed', () => {
    if (pythonProcess) pythonProcess.kill();
    if (process.platform !== 'darwin') app.quit();
});

app.on('before-quit', () => {
    if (pythonProcess) pythonProcess.kill();
});
```

- [ ] **Step 3: Write preload.js**

```javascript
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
    getBackendPort: () => ipcRenderer.invoke('get-backend-port'),
});
```

- [ ] **Step 4: Commit**

```bash
git add electron/
git commit -m "feat: Electron main process with Python lifecycle"
```

---

### Task 9: React types and API client

**Files:**
- Create: `src/types.ts`
- Create: `src/api.ts`
- Create: `src/index.tsx`

- [ ] **Step 1: Write types.ts**

```typescript
export interface Config {
  api_key: string;
  name: string;
  your_name: string;
  relationship: string;
  personality: string;
  extra: string;
  has_avatar: boolean;
}

export interface Message {
  role: 'user' | 'assistant';
  content: string;
}

export interface SetupRequest {
  api_key: string;
  name: string;
  your_name: string;
  relationship: string;
  personality: string;
  extra: string;
  chat_log: string;
}

export interface SetupResponse {
  status: string;
  message: string;
  has_persona: boolean;
}

export interface ChatResponse {
  reply: string;
  history: Message[];
}

export type AppStep = 'soul' | 'upload' | 'processing' | 'chat';
```

- [ ] **Step 2: Write api.ts**

```typescript
import type { Config, SetupRequest, SetupResponse, ChatResponse, Message } from './types';

let BASE_URL = '';

export async function initBackend(): Promise<void> {
  if (window.electronAPI) {
    const port = await window.electronAPI.getBackendPort();
    BASE_URL = `http://127.0.0.1:${port}`;
  } else {
    // Fallback for browser dev: check common ports
    BASE_URL = 'http://127.0.0.1:8000';
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Request failed');
  }
  return res.json();
}

export function healthCheck(): Promise<{ status: string }> {
  return request('/api/health');
}

export function runSetup(data: SetupRequest): Promise<SetupResponse> {
  return request('/api/setup', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export function sendMessage(message: string): Promise<ChatResponse> {
  return request('/api/chat', {
    method: 'POST',
    body: JSON.stringify({ message }),
  });
}

export function getHistory(): Promise<{ history: Message[] }> {
  return request('/api/chat/history');
}

export function getSettings(): Promise<Config> {
  return request('/api/settings');
}

export function updateSettings(data: Partial<Config>): Promise<{ status: string }> {
  return request('/api/settings', {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export function resetAll(): Promise<{ status: string }> {
  return request('/api/settings/reset', {
    method: 'DELETE',
  });
}
```

- [ ] **Step 3: Write index.tsx**

```tsx
import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import './App.css';

createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

- [ ] **Step 4: Write global type declaration**

Create `src/global.d.ts`:

```typescript
export {};

declare global {
  interface Window {
    electronAPI?: {
      getBackendPort: () => Promise<number>;
    };
  }
}
```

- [ ] **Step 5: Commit**

```bash
git add src/types.ts src/api.ts src/index.tsx src/global.d.ts
git commit -m "feat: React entry, types, and API client"
```

---

### Task 10: App shell and useSetup hook

**Files:**
- Create: `src/hooks/useSetup.ts`
- Create: `src/App.tsx`

- [ ] **Step 1: Write useSetup.ts**

```typescript
import { useState, useCallback } from 'react';
import type { AppStep, SetupRequest } from '../types';
import { runSetup, initBackend, healthCheck } from '../api';

export function useSetup() {
  const [step, setStep] = useState<AppStep>('soul');
  const [error, setError] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [backendReady, setBackendReady] = useState(false);

  const init = useCallback(async () => {
    try {
      await initBackend();
      await healthCheck();
      setBackendReady(true);
    } catch {
      // Retry after a delay for Python to start
      setTimeout(async () => {
        try {
          await initBackend();
          await healthCheck();
          setBackendReady(true);
        } catch {
          setError('无法连接到本地服务，请确认 Python 环境已安装。');
        }
      }, 3000);
    }
  }, []);

  const submitSoul = useCallback((_data: Partial<SetupRequest>) => {
    setStep('upload');
  }, []);

  const submitUpload = useCallback(async (data: SetupRequest) => {
    setStep('processing');
    setError('');
    setLoading(true);
    try {
      await runSetup(data);
      setStep('chat');
    } catch (e: any) {
      setError(e.message || '处理失败，请重试');
      setStep('upload');
    } finally {
      setLoading(false);
    }
  }, []);

  const goToSettings = useCallback(() => {
    // handled by App state
  }, []);

  return { step, setStep, error, loading, backendReady, init, submitSoul, submitUpload };
}
```

- [ ] **Step 2: Write App.tsx**

```tsx
import React, { useEffect, useState } from 'react';
import { useSetup } from './hooks/useSetup';
import { Wizard } from './components/Wizard';
import { ChatWindow } from './components/ChatWindow';
import { SettingsPanel } from './components/SettingsPanel';
import { getSettings } from './api';
import type { Config } from './types';

export default function App() {
  const { step, error, loading, backendReady, init, submitSoul, submitUpload } = useSetup();
  const [showSettings, setShowSettings] = useState(false);
  const [config, setConfig] = useState<Config | null>(null);

  useEffect(() => {
    init();
  }, [init]);

  useEffect(() => {
    if (backendReady) {
      getSettings().then(c => {
        setConfig(c);
        if (c.name && c.api_key) {
          // Already configured, go to chat
          // submitSoul handles transition
        }
      }).catch(() => {});
    }
  }, [backendReady]);

  if (!backendReady) {
    return (
      <div className="app-loading">
        <div className="spinner" />
        <p>正在启动…</p>
      </div>
    );
  }

  return (
    <div className="app">
      {step !== 'chat' ? (
        <Wizard
          step={step}
          error={error}
          loading={loading}
          onSubmitSoul={submitSoul}
          onSubmitUpload={submitUpload}
        />
      ) : (
        <ChatWindow onSettingsClick={() => setShowSettings(true)} />
      )}

      {showSettings && (
        <SettingsPanel
          onClose={() => setShowSettings(false)}
        />
      )}
    </div>
  );
}
```

- [ ] **Step 5: Commit**

```bash
git add src/hooks/useSetup.ts src/App.tsx
git commit -m "feat: App shell with setup flow routing"
```

---

### Task 11: Wizard component (3 steps)

**Files:**
- Create: `src/components/Wizard.tsx`

- [ ] **Step 1: Write Wizard.tsx**

```tsx
import React, { useState, useRef } from 'react';
import type { AppStep, SetupRequest } from '../types';

interface WizardProps {
  step: AppStep;
  error: string;
  loading: boolean;
  onSubmitSoul: (data: Partial<SetupRequest>) => void;
  onSubmitUpload: (data: SetupRequest) => void;
}

const RELATIONSHIPS = ['父母', '伴侣', '子女', '朋友', '其他'];

export function Wizard({ step, error, loading, onSubmitSoul, onSubmitUpload }: WizardProps) {
  const [apiKey, setApiKey] = useState('');
  const [name, setName] = useState('');
  const [yourName, setYourName] = useState('');
  const [relationship, setRelationship] = useState('');
  const [personality, setPersonality] = useState('');
  const [extra, setExtra] = useState('');
  const [chatLog, setChatLog] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleSoulSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmitSoul({ api_key: apiKey, name, your_name: yourName, relationship, personality, extra });
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      setChatLog(reader.result as string);
    };
    reader.readAsText(file);
  };

  const handleUploadSubmit = () => {
    onSubmitUpload({
      api_key: apiKey, name, your_name: yourName,
      relationship, personality, extra, chat_log: chatLog,
    });
  };

  if (step === 'processing') {
    return (
      <div className="wizard processing">
        <div className="spinner" />
        <h2>正在整理你们的回忆…</h2>
        <p className="sub">这可能需要几分钟，喝杯水等一会儿吧</p>
        {error && <p className="error-msg">{error}</p>}
      </div>
    );
  }

  if (step === 'soul') {
    return (
      <div className="wizard soul-step">
        <h2>让他离你更近一些</h2>
        <p className="sub">为了让对话更像他，请尽可能多地告诉我</p>

        {/* Avatar placeholder */}
        <div className="avatar-upload">
          <div className="avatar-circle">设置<br/>头像</div>
          <span className="avatar-hint">设置他的头像（可选）</span>
        </div>

        <form onSubmit={handleSoulSubmit}>
          <label>DeepSeek API Key</label>
          <input
            type="password"
            value={apiKey}
            onChange={e => setApiKey(e.target.value)}
            placeholder="sk-..."
            required
          />

          <div className="row">
            <div>
              <label>你对他的称呼</label>
              <input
                value={name}
                onChange={e => setName(e.target.value)}
                placeholder="例如：妈妈"
                required
              />
            </div>
            <div>
              <label>他叫你的名字</label>
              <input
                value={yourName}
                onChange={e => setYourName(e.target.value)}
                placeholder="例如：小宝"
              />
            </div>
          </div>

          <label>你们的关系</label>
          <div className="chips">
            {RELATIONSHIPS.map(r => (
              <button
                key={r}
                type="button"
                className={`chip ${relationship === r ? 'active' : ''}`}
                onClick={() => setRelationship(r)}
              >
                {r}
              </button>
            ))}
          </div>

          <label>他的性格特点</label>
          <textarea
            value={personality}
            onChange={e => setPersonality(e.target.value)}
            placeholder="描述他的说话方式和性格…"
            rows={3}
          />

          <label>关于他，你还想告诉我的</label>
          <textarea
            value={extra}
            onChange={e => setExtra(e.target.value)}
            placeholder="口头禅、你们的共同记忆、他对你的态度…"
            rows={2}
          />

          <button type="submit" className="btn-primary">下一步 →</button>
        </form>
      </div>
    );
  }

  // step === 'upload'
  return (
    <div className="wizard upload-step">
      <h2>加载记忆</h2>
      <p className="sub">上传你与他的聊天记录，越完整越好，时间跨度越长他越像本人</p>

      <div
        className="drop-zone"
        onClick={() => fileInputRef.current?.click()}
      >
        {chatLog ? (
          <p>已选择文件（{chatLog.length.toLocaleString()} 字）</p>
        ) : (
          <>
            <p>拖拽 TXT 文件到这里，或点击选择</p>
            <p className="hint">支持微信 / QQ 导出的聊天记录文件</p>
          </>
        )}
      </div>
      <input
        ref={fileInputRef}
        type="file"
        accept=".txt"
        onChange={handleFileChange}
        style={{ display: 'none' }}
      />

      {error && <p className="error-msg">{error}</p>}

      <button className="btn-primary" onClick={handleUploadSubmit}>
        开始整理回忆
      </button>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add src/components/Wizard.tsx
git commit -m "feat: 3-step wizard - soul, upload, processing"
```

---

### Task 12: Chat components

**Files:**
- Create: `src/components/MessageBubble.tsx`
- Create: `src/components/ChatWindow.tsx`
- Create: `src/hooks/useChat.ts`

- [ ] **Step 1: Write MessageBubble.tsx**

```tsx
import React from 'react';
import type { Message } from '../types';

interface Props {
  message: Message;
  aiName: string;
}

export function MessageBubble({ message, aiName }: Props) {
  const isUser = message.role === 'user';

  return (
    <div className={`message-row ${isUser ? 'user' : 'ai'}`}>
      {!isUser && <div className="avatar ai-avatar" />}
      <div className={`bubble ${isUser ? 'user-bubble' : 'ai-bubble'}`}>
        {message.content}
      </div>
      {isUser && <div className="avatar user-avatar" />}
    </div>
  );
}
```

- [ ] **Step 2: Write useChat.ts**

```typescript
import { useState, useCallback, useRef } from 'react';
import type { Message } from '../types';
import { sendMessage, getHistory } from '../api';

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isTyping, setIsTyping] = useState(false);
  const [error, setError] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const loadHistory = useCallback(async () => {
    try {
      const data = await getHistory();
      setMessages(data.history);
    } catch {}
  }, []);

  const send = useCallback(async (text: string) => {
    if (!text.trim()) return;
    setError('');

    const userMsg: Message = { role: 'user', content: text };
    setMessages(prev => [...prev, userMsg]);
    setIsTyping(true);

    try {
      const res = await sendMessage(text);
      const aiMsg: Message = { role: 'assistant', content: res.reply };
      setMessages(prev => [...prev, aiMsg]);
    } catch (e: any) {
      setError(e.message || '发送失败');
    } finally {
      setIsTyping(false);
    }
  }, []);

  return { messages, isTyping, error, send, loadHistory, messagesEndRef };
}
```

- [ ] **Step 3: Write ChatWindow.tsx**

```tsx
import React, { useEffect, useRef, useState } from 'react';
import { MessageBubble } from './MessageBubble';
import { useChat } from '../hooks/useChat';
import { getSettings } from '../api';

interface Props {
  onSettingsClick: () => void;
}

export function ChatWindow({ onSettingsClick }: Props) {
  const { messages, isTyping, error, send, loadHistory, messagesEndRef } = useChat();
  const [input, setInput] = useState('');
  const [aiName, setAiName] = useState('');
  const isFirstChat = messages.length === 0;

  useEffect(() => {
    loadHistory();
    getSettings().then(c => setAiName(c.name || '')).catch(() => {});
  }, [loadHistory]);

  const handleSend = () => {
    if (!input.trim()) return;
    send(input);
    setInput('');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="chat-window">
      <div className="chat-header">
        <div className="header-left">
          <div className="avatar ai-avatar small" />
          <span className="header-name">{aiName || '重逢'}</span>
        </div>
        <button className="gear-btn" onClick={onSettingsClick}>
          &#9881;
        </button>
      </div>

      <div className="chat-messages">
        {isFirstChat && (
          <div className="first-chat-banner">
            这是你们重逢的开始
          </div>
        )}

        {messages.map((msg, i) => (
          <MessageBubble key={i} message={msg} aiName={aiName} />
        ))}

        {isTyping && (
          <div className="typing-indicator">对方正在输入...</div>
        )}

        {error && <div className="error-msg">{error}</div>}
        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input-bar">
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="说点什么吧…"
        />
        <button onClick={handleSend} className="btn-send">发送</button>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Commit**

```bash
git add src/components/MessageBubble.tsx src/components/ChatWindow.tsx src/hooks/useChat.ts
git commit -m "feat: chat window with bubbles, typing indicator, input bar"
```

---

### Task 13: Settings panel and delete confirmation

**Files:**
- Create: `src/components/SettingsPanel.tsx`
- Create: `src/components/DeleteConfirm.tsx`

- [ ] **Step 1: Write SettingsPanel.tsx**

```tsx
import React, { useEffect, useState } from 'react';
import { getSettings, updateSettings, resetAll } from '../api';
import { DeleteConfirm } from './DeleteConfirm';
import type { Config } from '../types';

interface Props {
  onClose: () => void;
}

const RELATIONSHIPS = ['父母', '伴侣', '子女', '朋友', '其他'];

export function SettingsPanel({ onClose }: Props) {
  const [config, setConfig] = useState<Config>({
    api_key: '', name: '', your_name: '',
    relationship: '', personality: '', extra: '', has_avatar: false,
  });
  const [showDelete, setShowDelete] = useState(false);

  useEffect(() => {
    getSettings().then(setConfig).catch(() => {});
  }, []);

  const handleSave = async () => {
    await updateSettings(config);
    onClose();
  };

  const handleDelete = async () => {
    await resetAll();
    setShowDelete(false);
    onClose();
    window.location.reload();
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="settings-panel" onClick={e => e.stopPropagation()}>
        <div className="panel-header">
          <span>设置</span>
          <button className="close-btn" onClick={onClose}>&times;</button>
        </div>

        <div className="panel-body">
          <div className="avatar-upload">
            <div className="avatar-circle small">更换<br/>头像</div>
            <span>更换头像</span>
          </div>

          <label>DeepSeek API Key</label>
          <input
            type="password"
            value={config.api_key}
            onChange={e => setConfig({ ...config, api_key: e.target.value })}
            placeholder="sk-..."
          />

          <div className="row">
            <div>
              <label>你对他的称呼</label>
              <input
                value={config.name}
                onChange={e => setConfig({ ...config, name: e.target.value })}
              />
            </div>
            <div>
              <label>他叫你的名字</label>
              <input
                value={config.your_name}
                onChange={e => setConfig({ ...config, your_name: e.target.value })}
              />
            </div>
          </div>

          <label>你们的关系</label>
          <div className="chips">
            {RELATIONSHIPS.map(r => (
              <button
                key={r}
                type="button"
                className={`chip ${config.relationship === r ? 'active' : ''}`}
                onClick={() => setConfig({ ...config, relationship: r })}
              >
                {r}
              </button>
            ))}
          </div>

          <label>他的性格特点</label>
          <textarea
            value={config.personality}
            onChange={e => setConfig({ ...config, personality: e.target.value })}
            rows={3}
          />

          <label>关于他，你还想告诉我的</label>
          <textarea
            value={config.extra}
            onChange={e => setConfig({ ...config, extra: e.target.value })}
            rows={2}
          />

          <p className="update-hint">修改后会逐渐体现在对话中</p>

          <button className="btn-primary" onClick={handleSave}>保存修改</button>

          <div className="divider" />

          <div className="delete-section">
            <p>需要重新来过吗？</p>
            <button className="btn-delete" onClick={() => setShowDelete(true)}>
              删除并重新创建
            </button>
          </div>
        </div>
      </div>

      {showDelete && (
        <DeleteConfirm
          onCancel={() => setShowDelete(false)}
          onConfirm={handleDelete}
        />
      )}
    </div>
  );
}
```

- [ ] **Step 2: Write DeleteConfirm.tsx**

```tsx
import React from 'react';

interface Props {
  onCancel: () => void;
  onConfirm: () => void;
}

export function DeleteConfirm({ onCancel, onConfirm }: Props) {
  return (
    <div className="modal-overlay" onClick={onCancel}>
      <div className="confirm-dialog" onClick={e => e.stopPropagation()}>
        <h3>确定要重新开始吗？</h3>
        <p>
          现在的聊天记录、设置和记忆都会被清除。<br />
          如果你想保留，可以先导出聊天记录。
        </p>
        <div className="confirm-buttons">
          <button className="btn-cancel" onClick={onCancel}>再想想</button>
          <button className="btn-confirm-delete" onClick={onConfirm}>确定删除</button>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add src/components/SettingsPanel.tsx src/components/DeleteConfirm.tsx
git commit -m "feat: settings panel with editable fields + delete flow"
```

---

### Task 14: Global styles (warm theme)

**Files:**
- Create: `src/App.css`

- [ ] **Step 1: Write App.css**

```css
/* === Reset & Base === */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --bg: #faf8f5;
  --bg-warm: #f5f0ea;
  --text: #5c4f3e;
  --text-light: #8c7a6b;
  --text-muted: #b8a898;
  --accent: #c4a090;
  --accent-light: #e8ddd0;
  --white: #ffffff;
  --border: #d4c8b8;
  --shadow: 0 1px 2px rgba(0,0,0,0.05);
  --radius: 12px;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", sans-serif;
  background: var(--bg);
  color: var(--text);
  font-size: 14px;
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
}

#root { height: 100vh; }

.app { height: 100vh; display: flex; flex-direction: column; }

/* === Loading === */
.app-loading {
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  height: 100vh; gap: 16px; color: var(--text-light);
}

/* === Spinner === */
.spinner {
  width: 36px; height: 36px;
  border: 3px solid var(--accent-light);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* === Wizard === */
.wizard {
  padding: 40px 28px; max-width: 400px; margin: 0 auto;
  width: 100%; height: 100vh; overflow-y: auto;
}
.wizard h2 { font-size: 18px; font-weight: 500; color: var(--text); margin-bottom: 8px; }
.wizard .sub { color: var(--text-light); font-size: 13px; margin-bottom: 24px; }

.wizard label {
  display: block; font-size: 12px; color: var(--text-light);
  margin-bottom: 4px; margin-top: 16px;
}

.wizard input[type="text"],
.wizard input[type="password"],
.wizard textarea {
  width: 100%; padding: 10px 12px;
  border: 1px solid var(--border); border-radius: 8px;
  background: var(--white); color: var(--text);
  font-size: 13px; font-family: inherit;
  resize: none;
}
.wizard input:focus, .wizard textarea:focus {
  outline: none; border-color: var(--accent);
}

.wizard .row { display: flex; gap: 12px; }
.wizard .row > div { flex: 1; }

/* === Chips === */
.chips { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 4px; }
.chip {
  padding: 4px 14px; border-radius: 12px; border: 1px solid var(--border);
  background: var(--white); color: var(--text-light);
  font-size: 12px; cursor: pointer; font-family: inherit;
}
.chip.active { background: var(--accent-light); color: var(--text); border-color: var(--accent-light); }

/* === Avatar === */
.avatar-upload {
  display: flex; align-items: center; gap: 14px; margin-bottom: 20px;
}
.avatar-circle {
  width: 56px; height: 56px; border-radius: 50%;
  background: var(--accent-light); color: var(--text-muted);
  display: flex; align-items: center; justify-content: center;
  font-size: 11px; text-align: center; cursor: pointer;
  line-height: 1.3; flex-shrink: 0;
}
.avatar-circle.small { width: 32px; height: 32px; font-size: 8px; }
.avatar-hint { color: var(--text-muted); font-size: 11px; }

/* === Buttons === */
.btn-primary {
  width: 100%; padding: 10px; margin-top: 20px;
  border: none; border-radius: 8px;
  background: var(--accent); color: white;
  font-size: 14px; cursor: pointer; font-family: inherit;
}
.btn-primary:hover { opacity: 0.9; }

/* === Drop zone === */
.drop-zone {
  border: 2px dashed var(--border); border-radius: var(--radius);
  padding: 32px; text-align: center; cursor: pointer;
  color: var(--text-muted); margin-bottom: 16px;
}
.drop-zone .hint { font-size: 11px; color: var(--text-muted); margin-top: 4px; }

/* === Processing === */
.processing { text-align: center; display: flex; flex-direction: column; align-items: center; justify-content: center; }
.processing .spinner { margin-bottom: 20px; }

/* === Chat Window === */
.chat-window { height: 100vh; display: flex; flex-direction: column; }

.chat-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 16px; background: var(--bg-warm);
  border-bottom: 1px solid var(--border);
  -webkit-app-region: drag;
}
.chat-header .header-left { display: flex; align-items: center; gap: 10px; }
.chat-header .header-name { font-size: 15px; font-weight: 500; }
.gear-btn {
  background: none; border: none; font-size: 18px;
  color: var(--text-muted); cursor: pointer;
  -webkit-app-region: no-drag;
}

/* === Messages === */
.chat-messages {
  flex: 1; overflow-y: auto; padding: 16px;
  display: flex; flex-direction: column; gap: 14px;
}
.first-chat-banner {
  text-align: center; color: var(--text-muted);
  font-size: 11px; padding: 6px 12px;
  background: var(--bg-warm); border-radius: 10px;
  align-self: center; margin-bottom: 8px;
}
.message-row { display: flex; gap: 8px; align-items: flex-end; }
.message-row.user { justify-content: flex-end; }
.avatar {
  width: 28px; height: 28px; border-radius: 50%; flex-shrink: 0;
}
.ai-avatar { background: var(--accent); }
.user-avatar { background: var(--border); }

.bubble {
  max-width: 65%; padding: 10px 14px; border-radius: 16px;
  font-size: 14px; line-height: 1.5; word-break: break-word;
}
.user-bubble {
  background: var(--accent-light); color: var(--text);
  border-radius: 16px 16px 4px 16px;
}
.ai-bubble {
  background: var(--white); color: var(--text);
  border-radius: 16px 16px 16px 4px;
  box-shadow: var(--shadow);
}

/* === Typing === */
.typing-indicator {
  text-align: center; color: var(--text-muted);
  font-size: 12px; padding: 6px 0;
}

/* === Input Bar === */
.chat-input-bar {
  display: flex; gap: 8px; padding: 12px 16px;
  border-top: 1px solid var(--border); background: var(--white);
}
.chat-input-bar input {
  flex: 1; padding: 10px 14px;
  border: 1px solid var(--border); border-radius: 20px;
  font-size: 13px; font-family: inherit; outline: none;
}
.chat-input-bar input:focus { border-color: var(--accent); }
.btn-send {
  padding: 8px 18px; border: none; border-radius: 20px;
  background: var(--accent); color: white;
  font-size: 13px; cursor: pointer; font-family: inherit;
}

/* === Settings Panel === */
.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.3);
  display: flex; align-items: center; justify-content: center;
  z-index: 100;
}
.settings-panel {
  background: var(--bg); border-radius: var(--radius);
  width: 380px; max-height: 85vh; overflow-y: auto;
  box-shadow: 0 8px 32px rgba(0,0,0,0.12);
}
.panel-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 14px 18px; border-bottom: 1px solid var(--border);
  font-size: 15px; font-weight: 500;
}
.close-btn { background: none; border: none; font-size: 18px; color: var(--text-muted); cursor: pointer; }
.panel-body { padding: 18px; }
.panel-body label { display: block; font-size: 12px; color: var(--text-light); margin-bottom: 4px; margin-top: 14px; }
.panel-body input, .panel-body textarea {
  width: 100%; padding: 10px 12px;
  border: 1px solid var(--border); border-radius: 8px;
  font-size: 13px; font-family: inherit; resize: none;
}
.panel-body .row { display: flex; gap: 12px; }
.panel-body .row > div { flex: 1; }
.update-hint { color: var(--text-muted); font-size: 11px; margin-top: 16px; }

.divider { border-top: 1px solid var(--border); margin: 24px 0; }

.delete-section { text-align: center; }
.delete-section p { color: var(--text-muted); font-size: 12px; margin-bottom: 12px; }
.btn-delete {
  background: none; border: 1px solid var(--border);
  color: var(--text-muted); padding: 8px 28px;
  border-radius: 8px; font-size: 13px; cursor: pointer; font-family: inherit;
}

/* === Delete Confirm === */
.confirm-dialog {
  background: var(--bg); border-radius: var(--radius);
  padding: 24px; text-align: center; width: 320px;
}
.confirm-dialog h3 { font-size: 15px; font-weight: 500; margin-bottom: 8px; }
.confirm-dialog p { color: var(--text-light); font-size: 12px; margin-bottom: 20px; line-height: 1.6; }
.confirm-buttons { display: flex; gap: 12px; justify-content: center; }
.btn-cancel {
  background: none; border: 1px solid var(--border);
  color: var(--text-light); padding: 8px 22px;
  border-radius: 8px; font-size: 13px; cursor: pointer; font-family: inherit;
}
.btn-confirm-delete {
  background: var(--accent); border: none; color: white;
  padding: 8px 22px; border-radius: 8px;
  font-size: 13px; cursor: pointer; font-family: inherit;
}

/* === Error === */
.error-msg {
  color: #b09080; font-size: 12px; text-align: center;
  margin-top: 8px; padding: 8px; background: #faf0ed;
  border-radius: 8px;
}
```

- [ ] **Step 2: Commit**

```bash
git add src/App.css
git commit -m "feat: warm minimal theme styles"
```

---

### Task 15: Integration — port handoff and end-to-end wiring

**Files:**
- Modify: `electron/main.js` (verify IPC)
- Check: all files exist and imports match

- [ ] **Step 1: Verify all file paths and imports**

Checklist:
- [ ] `backend/main.py` imports all routers correctly
- [ ] `backend/api/setup.py` imports from `rag.*`, `persona.*`, `config`
- [ ] `backend/api/chat.py` imports from `agent.loop`, `chat.history`, `config`
- [ ] `backend/agent/loop.py` imports from `rag.*`, `persona.correction`, `config`
- [ ] `src/App.tsx` imports from all components and hooks
- [ ] `src/api.ts` base URL initialization works with Electron preload

- [ ] **Step 2: Run backend standalone test**

```bash
cd backend
python -c "
from main import app
from fastapi.testclient import TestClient
client = TestClient(app)
r = client.get('/api/health')
assert r.status_code == 200
assert r.json() == {'status': 'ok'}
print('Backend health check: PASS')
"
```

- [ ] **Step 3: Install Python dependencies**

```bash
cd backend
pip install -r requirements.txt
```

- [ ] **Step 4: Run full backend smoke test**

```bash
cd backend
python -c "
from main import app
from fastapi.testclient import TestClient
client = TestClient(app)

# Test settings
r = client.get('/api/settings')
assert r.status_code == 200

# Test chat without config (should fail gracefully)
r = client.post('/api/chat', json={'message': 'hello'})
assert r.status_code == 400  # no api_key set

print('Full backend smoke test: PASS')
"
```

- [ ] **Step 5: Run frontend build check**

```bash
npm run build
```
Expected: `dist/renderer/index.html` and assets created.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat: complete MVP integration wiring"
```

---

## Summary

**22 files created** across 3 layers:

| Layer | Files | Purpose |
|-------|-------|---------|
| Python backend | 13 | FastAPI, RAG, persona distillation, agent loop, chat history |
| Electron shell | 2 | Main process, Python lifecycle, preload bridge |
| React frontend | 7 | Wizard, chat, settings, warm theme |

**To run in development:**

```bash
# Terminal 1: Start Python backend
cd backend
pip install -r requirements.txt
python main.py

# Terminal 2: Start Electron + Vite
npm install
npm run electron:dev
```

**Post-MVP upgrade path:**
- `pyinstaller` to bundle Python runtime
- `electron-builder` to produce .exe installer
- QQ/WeChat channel support via OpenClaw integration
