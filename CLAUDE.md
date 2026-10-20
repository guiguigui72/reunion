# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What is this

重逢 (Reunion) is a desktop AI companion that mimics a deceased loved one. Users upload chat logs, and the app generates an AI that speaks in that person's voice. Built with Electron + React frontend and Python FastAPI backend.

## Commands

```bash
# Install frontend deps
npm install

# Install backend deps (requires Python 3.9+)
pip install -r backend/requirements.txt

# Development (starts Vite + Electron + Python backend all at once)
npm run electron:dev

# Frontend build only (no Python, no Electron)
npm run build

# Windows one-click setup
setup.bat
```

There are no tests yet — this is an MVP.

## Architecture

The app has two layers that communicate over localhost HTTP:

**Electron shell** (`electron/main.js`) spawns a Python subprocess on startup, reads its port from a temp file, and loads the React frontend. On exit it kills the subprocess.

**React frontend** (`src/`) handles all UI. Steps through a 5-screen guided onboarding wizard → chat window with settings.

**Python backend** (`backend/main.py`) runs FastAPI with dynamic port allocation. All AI work happens here: persona distillation, RAG retrieval, LLM calls, correction handling.

### Key data flow

1. User fills guided onboarding (soul info + chat log upload)
2. `POST /api/setup` → `distiller.distill_persona()` runs 2 LLM calls using dot-skill's native prompts, produces a 6-layer persona.md; chat log is chunked and embedded into ChromaDB
3. `POST /api/chat` → `agent.loop.chat()` classifies intent (correction/memory_search/chat), optionally searches ChromaDB, builds prompt with persona + guardrails + history + memory fragments, calls DeepSeek

### The distillation pipeline

Uses dot-skill's native prompt files from `backend/prompts/` (fetched from titanwings/colleague-skill):
- `persona_analyzer.md` → extracts structured fields (catchphrases, triggers, conflict patterns, etc.)
- `persona_builder.md` → fills 6-layer template with real example replies
- `merger.md` → incremental persona updates when user changes settings
- `correction_handler.md` → in-character response when user corrects AI behavior

The `intake.md` prompt is **not used** — replaced by the React guided onboarding form.

### Process management

- Python uses `port=0` to find a free port, writes it to `os.tmpdir()/reunion_port.txt`
- Electron reads this file with retries (30 attempts, 1s interval)
- `ipcMain.handle('get-backend-port')` exposes port to renderer via `electronAPI.getBackendPort()`

### Storage

All user data in `~/.reunion/`:
- `config.json` — user settings (api_key, name, personality, etc.)
- `persona.md` — generated 6-layer System Prompt
- `chat_history.db` — SQLite conversation log
- `chroma/` — ChromaDB vector embeddings
- `avatar.png` — optional avatar image

## Key constraints

- The app speaks Chinese. All UI copy follows a warm, minimal tone — no technical jargon, no red error icons, no progress percentages
- Persona is stored as a System Prompt, not as raw data. The AI reads it fresh every conversation
- Avatar is stored locally, never uploaded anywhere
- The `correction_handler.md` prompt is raw dot-skill content designed for an interactive Agent host — we override it with an in-character-only system message to prevent the LLM from switching to "engineer mode"
- Python 3.13 requires `from __future__ import annotations` for union type syntax (`X | None`) in runtime contexts (see `rag/store.py`, `rag/embedder.py`)
