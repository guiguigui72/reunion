# 对话式引导 + 智能追问 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace two open-ended textareas with 3-screen guided Q&A (dot-skill intake structure) + LLM-generated smart follow-up questions after chat log analysis.

**Architecture:** Wizard gains 3 sub-screens for guided intake (`'guide_1a' | 'guide_1b' | 'guide_1c'` replacing `'soul'`), plus a new `'smart_questions'` step after upload. Backend `/api/setup` gains entity extraction and returns `questions[]`; new `POST /api/setup/answers` merges user answers into persona.

**Tech Stack:** React (TypeScript), Python FastAPI, DeepSeek API.

---

## File Structure

```
Modified:
├── src/types.ts                          # +Question type, +AppStep values, +SetupResponse.questions
├── src/api.ts                            # +submitAnswers()
├── src/hooks/useSetup.ts                 # rewrite state machine
├── src/App.tsx                           # pass new handlers to Wizard
├── src/components/Wizard.tsx             # 5 screens instead of 2
├── backend/persona/distiller.py          # +extract_entities(), +merge_answers()
├── backend/api/setup.py                  # questions in response, /api/setup/answers endpoint
```

---

### Task 1: Backend — extract_entities + merge_answers

**Files:**
- Modify: `backend/persona/distiller.py`

- [ ] **Step 1: Add extract_entities() and merge_answers()**

Append to `backend/persona/distiller.py`:

```python
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
```

- [ ] **Step 2: Commit**

```bash
cd D:\重逢2 && git add backend/persona/distiller.py && git commit -m "feat: extract_entities + merge_answers for smart follow-up"
```

---

### Task 2: Backend — update /api/setup + add /api/setup/answers

**Files:**
- Modify: `backend/api/setup.py`

- [ ] **Step 1: Update imports and SetupResponse model**

Replace the top section (lines 1-9) and add new models:

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from config import save_config, load_config
from rag.chunker import chunk_text, extract_target_only
from rag.embedder import embed_texts
from rag.store import get_or_create_collection
from persona.distiller import distill_persona, extract_entities, merge_answers

router = APIRouter()


class SetupRequest(BaseModel):
    api_key: str
    name: str
    your_name: str = ""
    relationship: str = ""
    personality: str = ""
    extra: str = ""
    chat_log: str = ""


class AnswerItem(BaseModel):
    entity: str
    type: str = ""
    detail: str = ""
    context_hint: str = ""


class AnswersRequest(BaseModel):
    api_key: str
    answers: list[AnswerItem]
```

- [ ] **Step 2: Add questions to setup response**

Replace the `return` statement at the end of the `/api/setup` endpoint (line 68-72):

```python
    # Extract entities for smart follow-up
    questions = []
    if req.chat_log.strip():
        try:
            questions = extract_entities(req.chat_log, req.api_key)
        except Exception:
            questions = []

    return {
        "status": "ok",
        "message": "设置完成",
        "has_persona": bool(persona),
        "questions": questions,
    }
```

- [ ] **Step 3: Add POST /api/setup/answers endpoint**

Add after the `/api/setup` endpoint:

```python
@router.post("/api/setup/answers")
async def submit_answers(req: AnswersRequest):
    if not req.api_key or not req.answers:
        raise HTTPException(status_code=400, detail="api_key and answers are required")

    try:
        answers = [a.model_dump() for a in req.answers]
        merge_answers(answers, req.api_key)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"答案合并失败: {str(e)}")

    return {"status": "ok"}
```

- [ ] **Step 4: Commit**

```bash
cd D:\重逢2 && git add backend/api/setup.py && git commit -m "feat: setup returns questions, add answers endpoint"
```

---

### Task 3: Frontend — types + API client

**Files:**
- Modify: `src/types.ts`
- Modify: `src/api.ts`

- [ ] **Step 1: Update types.ts**

Replace the entire file:

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

export interface Question {
  entity: string;
  context: string;
  type: 'pet' | 'person' | 'place' | 'object' | 'generic';
  context_hint: string;
}

export interface AnswerItem {
  entity: string;
  type: string;
  detail: string;
  context_hint: string;
}

export interface SetupResponse {
  status: string;
  message: string;
  has_persona: boolean;
  questions: Question[];
}

export interface ChatResponse {
  reply: string;
  history: Message[];
}

export type AppStep = 'guide_1a' | 'guide_1b' | 'guide_1c' | 'upload' | 'smart_questions' | 'processing' | 'chat';
```

- [ ] **Step 2: Add submitAnswers() to api.ts**

Add after `getAvatarUrl()` at the end of the file:

```typescript
export async function submitAnswers(apiKey: string, answers: AnswerItem[]): Promise<void> {
  await request('/api/setup/answers', {
    method: 'POST',
    body: JSON.stringify({ api_key: apiKey, answers }),
  });
}
```

Also update the import line to include `AnswerItem`:

```typescript
import type { Config, SetupRequest, SetupResponse, ChatResponse, Message, AnswerItem } from './types';
```

- [ ] **Step 3: Build to verify**

```bash
cd D:\重逢2 && npm run build
```
Expected: `✓ 35 modules transformed.`

- [ ] **Step 4: Commit**

```bash
cd D:\重逢2 && git add src/types.ts src/api.ts && git commit -m "feat: add Question/AnswerItem types, submitAnswers API"
```

---

### Task 4: Frontend — useSetup state machine rewrite

**Files:**
- Modify: `src/hooks/useSetup.ts`

- [ ] **Step 1: Rewrite useSetup.ts**

Replace the entire file:

```typescript
import { useState, useCallback } from 'react';
import type { AppStep, SetupRequest, AnswerItem } from '../types';
import { runSetup, initBackend, healthCheck, submitAnswers } from '../api';

export function useSetup() {
  const [step, setStep] = useState<AppStep>('guide_1a');
  const [error, setError] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [backendReady, setBackendReady] = useState(false);

  // Accumulated data across all guide screens + upload
  const [setupData, setSetupData] = useState<Partial<SetupRequest>>({});
  const [questions, setQuestions] = useState<AnswerItem[]>([]);

  const init = useCallback(async () => {
    try {
      await initBackend();
      await healthCheck();
      setBackendReady(true);
    } catch {
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

  // Guide 1a → 1b
  const submit1a = useCallback((data: Partial<SetupRequest>) => {
    setSetupData(prev => ({ ...prev, ...data }));
    setStep('guide_1b');
  }, []);

  // Guide 1b → 1c
  const submit1b = useCallback((personality: string) => {
    setSetupData(prev => ({ ...prev, personality }));
    setStep('guide_1c');
  }, []);

  // Guide 1c → upload
  const submit1c = useCallback((extra: string) => {
    setSetupData(prev => ({ ...prev, extra }));
    setStep('upload');
  }, []);

  // Upload → processing (runs setup, receives questions)
  const submitUpload = useCallback(async (chatLog: string) => {
    const fullData: SetupRequest = {
      api_key: setupData.api_key || '',
      name: setupData.name || '',
      your_name: setupData.your_name || '',
      relationship: setupData.relationship || '',
      personality: setupData.personality || '',
      extra: setupData.extra || '',
      chat_log: chatLog,
    };

    setStep('processing');
    setError('');
    setLoading(true);
    try {
      const res = await runSetup(fullData);
      if (res.questions && res.questions.length > 0) {
        const qs: AnswerItem[] = res.questions.map(q => ({
          entity: q.entity,
          type: '',
          detail: '',
          context_hint: q.context_hint,
        }));
        setQuestions(qs);
        setStep('smart_questions');
      } else {
        setStep('chat');
      }
    } catch (e: any) {
      setError(e.message || '处理失败，请重试');
      setStep('upload');
    } finally {
      setLoading(false);
    }
  }, [setupData]);

  // Smart questions → processing → chat
  const submitAnswersAndContinue = useCallback(async () => {
    const apiKey = setupData.api_key || '';
    setStep('processing');
    setError('');
    setLoading(true);
    try {
      if (questions.some(q => q.type || q.detail)) {
        await submitAnswers(apiKey, questions.filter(q => q.type || q.detail));
      }
      setStep('chat');
    } catch (e: any) {
      setError(e.message || '处理失败');
      setStep('smart_questions');
    } finally {
      setLoading(false);
    }
  }, [questions, setupData.api_key]);

  // Smart questions: update a single answer
  const updateAnswer = useCallback((index: number, updates: Partial<AnswerItem>) => {
    setQuestions(prev => prev.map((q, i) => i === index ? { ...q, ...updates } : q));
  }, []);

  // Back navigation
  const goBack = useCallback(() => {
    const transitions: Record<AppStep, AppStep> = {
      'guide_1b': 'guide_1a',
      'guide_1c': 'guide_1b',
      'upload': 'guide_1c',
      'smart_questions': 'upload',
      'guide_1a': 'guide_1a',
      'processing': 'processing',
      'chat': 'chat',
    };
    setStep(transitions[step] || step);
  }, [step]);

  return {
    step, setStep, error, loading, backendReady, init,
    setupData, questions,
    submit1a, submit1b, submit1c, submitUpload,
    submitAnswersAndContinue, updateAnswer, goBack,
  };
}
```

- [ ] **Step 2: Build to verify**

```bash
cd D:\重逢2 && npm run build
```
Expected: build passes.

- [ ] **Step 3: Commit**

```bash
cd D:\重逢2 && git add src/hooks/useSetup.ts && git commit -m "feat: 5-step state machine for guided onboarding"
```

---

### Task 5: Frontend — Wizard.tsx rewrite (all 5 screens)

**Files:**
- Modify: `src/components/Wizard.tsx`

- [ ] **Step 1: Rewrite Wizard.tsx**

Replace the entire file:

```tsx
import React, { useState, useRef } from 'react';
import type { AppStep, SetupRequest, AnswerItem } from '../types';
import { uploadAvatar, getAvatarUrl } from '../api';

interface WizardProps {
  step: AppStep;
  error: string;
  loading: boolean;
  setupData: Partial<SetupRequest>;
  questions: AnswerItem[];
  submit1a: (data: Partial<SetupRequest>) => void;
  submit1b: (personality: string) => void;
  submit1c: (extra: string) => void;
  submitUpload: (chatLog: string) => void;
  submitAnswersAndContinue: () => void;
  updateAnswer: (index: number, updates: Partial<AnswerItem>) => void;
  onBack: () => void;
}

const RELATIONSHIPS = ['父母', '伴侣', '子女', '朋友', '其他'];

const PET_CHIPS = ['是宠物狗', '是宠物猫', '是其他宠物', '不是宠物'];
const PERSON_CHIPS = ['家人', '朋友', '同事', '其他认识的人'];
const PLACE_CHIPS = ['家', '老家', '工作的地方', '常去的地方', '其他'];

function getChipsForType(type: string): string[] {
  switch (type) {
    case 'pet': return PET_CHIPS;
    case 'person': return PERSON_CHIPS;
    case 'place': return PLACE_CHIPS;
    default: return [];
  }
}

export function Wizard({
  step, error, loading, setupData, questions,
  submit1a, submit1b, submit1c, submitUpload,
  submitAnswersAndContinue, updateAnswer, onBack,
}: WizardProps) {
  // === Step 1a state ===
  const [apiKey, setApiKey] = useState(setupData.api_key || '');
  const [name, setName] = useState(setupData.name || '');
  const [yourName, setYourName] = useState(setupData.your_name || '');
  const [relationship, setRelationship] = useState(setupData.relationship || '');
  const [lastSeen, setLastSeen] = useState('');
  const [birthYear, setBirthYear] = useState('');
  const [zodiac, setZodiac] = useState('');
  const [avatarFile, setAvatarFile] = useState<File | null>(null);
  const [avatarPreview, setAvatarPreview] = useState('');
  const avatarInputRef = useRef<HTMLInputElement>(null);

  // === Step 1b state ===
  const [angerStyle, setAngerStyle] = useState('');
  const [careStyle, setCareStyle] = useState('');
  const [habit, setHabit] = useState('');

  // === Step 1c state ===
  const [memory, setMemory] = useState('');

  // === Upload state ===
  const [chatLog, setChatLog] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleAvatarChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setAvatarFile(file);
    const reader = new FileReader();
    reader.onload = () => setAvatarPreview(reader.result as string);
    reader.readAsDataURL(file);
  };

  const handle1aSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (avatarFile) {
      try { await uploadAvatar(avatarFile); } catch {}
    }
    submit1a({
      api_key: apiKey, name, your_name: yourName, relationship,
      personality: '', extra: '',
    });
  };

  const handle1bSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const lines = [
      angerStyle ? `不开心时：${angerStyle}` : '',
      careStyle ? `关心时：${careStyle}` : '',
      habit ? `习惯/口头禅：${habit}` : '',
    ].filter(Boolean);
    submit1b(lines.join('；'));
  };

  const handle1cSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    submit1c(memory);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => setChatLog(reader.result as string);
    reader.readAsText(file);
  };

  // ============ Processing ============
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

  // ============ Step 1a: 基本信息 ============
  if (step === 'guide_1a') {
    return (
      <div className="wizard soul-step">
        <h2>让他离你更近一些</h2>
        <p className="sub">为了让对话更像他，请尽可能多地告诉我</p>

        <div className="avatar-upload">
          <div
            className="avatar-circle"
            onClick={() => avatarInputRef.current?.click()}
            style={avatarPreview ? {
              backgroundImage: `url(${avatarPreview})`,
              backgroundSize: 'cover', backgroundPosition: 'center', color: 'transparent',
            } : {}}
          >
            {!avatarPreview && <>设置<br/>头像</>}
          </div>
          <div>
            <p style={{ color: '#5c4f3e', fontSize: '13px', margin: 0 }}>放一张他的照片吧</p>
            <p style={{ color: '#b8a898', fontSize: '11px', margin: '2px 0 0' }}>不设也没关系，聊天的感觉不会差</p>
          </div>
          <input ref={avatarInputRef} type="file" accept="image/*" onChange={handleAvatarChange} style={{ display: 'none' }} />
        </div>

        <form onSubmit={handle1aSubmit}>
          <label>DeepSeek API Key</label>
          <input type="password" value={apiKey} onChange={e => setApiKey(e.target.value)} placeholder="sk-..." required />
          <p style={{ color: '#b8a898', fontSize: '11px', margin: '2px 0 0' }}>你的密钥只会存在本地，不会上传到任何地方</p>

          <label style={{ marginTop: 20 }}>你怎么称呼他？</label>
          <input value={name} onChange={e => setName(e.target.value)} placeholder="妈妈、外婆、阿杰…" required />

          <label>他平时怎么叫你？</label>
          <input value={yourName} onChange={e => setYourName(e.target.value)} placeholder="小宝、囡囡、或者你的名字…" />

          <label>你们的关系</label>
          <div className="chips">
            {RELATIONSHIPS.map(r => (
              <button key={r} type="button" className={`chip ${relationship === r ? 'active' : ''}`} onClick={() => setRelationship(r)}>{r}</button>
            ))}
          </div>

          <label>上次见到他，是什么时候的事了？</label>
          <input value={lastSeen} onChange={e => setLastSeen(e.target.value)} placeholder="一年多了、上个月、记不太清了…" />

          <div className="row">
            <div>
              <label>他是哪一年出生的？</label>
              <input value={birthYear} onChange={e => setBirthYear(e.target.value)} placeholder="1968 年、属猴的…" />
            </div>
            <div>
              <label>他的星座和 MBTI？</label>
              <input value={zodiac} onChange={e => setZodiac(e.target.value)} placeholder="不记得也没关系" />
            </div>
          </div>

          <p style={{ color: '#b8a898', fontSize: '11px', marginTop: 8 }}>想到多少填多少，后面的问题也都可以跳过</p>

          <button type="submit" className="btn-primary">继续 →</button>
        </form>
      </div>
    );
  }

  // ============ Step 1b: 性格速写 ============
  if (step === 'guide_1b') {
    return (
      <div className="wizard soul-step">
        <h2>他待人是什么样子的？</h2>
        <p className="sub">想到什么说什么，不用太认真</p>

        <form onSubmit={handle1bSubmit}>
          <label>不开心的时候，他会怎么做？</label>
          <textarea value={angerStyle} onChange={e => setAngerStyle(e.target.value)} placeholder="沉默不说话、会走开、会一直念叨…" rows={2} />

          <label>他关心你的时候，是什么样的？</label>
          <textarea value={careStyle} onChange={e => setCareStyle(e.target.value)} placeholder="一直问吃了吗、嘴上不说话但什么都帮你做了…" rows={2} />

          <label>他有什么改不掉的小习惯？</label>
          <input value={habit} onChange={e => setHabit(e.target.value)} placeholder="爱说「你看看你」、出门前总要折回来一次…" />

          <p style={{ color: '#b8a898', fontSize: '11px', marginTop: 8 }}>不想答的就跳过去</p>

          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 16 }}>
            <button type="button" className="back-btn" onClick={onBack}>← 上一步</button>
            <button type="submit" className="btn-primary" style={{ width: 'auto', marginTop: 0 }}>继续 →</button>
          </div>
        </form>
      </div>
    );
  }

  // ============ Step 1c: 一个记忆 ============
  if (step === 'guide_1c') {
    return (
      <div className="wizard soul-step">
        <h2>跟我说一件你们之间的事吧</h2>
        <p className="sub">不用是什么大事，就是到现在想起来，心里还会动一下的那种</p>

        <form onSubmit={handle1cSubmit}>
          <textarea value={memory} onChange={e => setMemory(e.target.value)} placeholder="想到什么就写下来…" rows={4} />

          <p style={{ color: '#b8a898', fontSize: '11px', marginTop: 8 }}>不说也没关系</p>

          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 16 }}>
            <button type="button" className="back-btn" onClick={onBack}>← 上一步</button>
            <button type="submit" className="btn-primary" style={{ width: 'auto', marginTop: 0 }}>说完了，下一步 →</button>
          </div>
        </form>
      </div>
    );
  }

  // ============ Step 2: 上传聊天记录 ============
  return step === 'upload' ? (
    <div className="wizard upload-step">
      <button type="button" className="back-btn" onClick={onBack}>&#8592; 上一步</button>
      <h2>加载记忆</h2>
      <p className="sub">上传你与他的聊天记录，越完整越好，时间跨度越长他越像本人</p>

      <div className="drop-zone" onClick={() => fileInputRef.current?.click()}>
        {chatLog ? (
          <p>已选择文件（{chatLog.length.toLocaleString()} 字）</p>
        ) : (
          <>
            <p>拖拽 TXT 文件到这里，或点击选择</p>
            <p className="hint">支持微信 / QQ 导出的聊天记录文件</p>
          </>
        )}
      </div>
      <input ref={fileInputRef} type="file" accept=".txt" onChange={handleFileChange} style={{ display: 'none' }} />
      {error && <p className="error-msg">{error}</p>}
      <button className="btn-primary" onClick={() => submitUpload(chatLog)} disabled={!chatLog}>开始整理回忆</button>
    </div>
  ) : (
    // ============ Step 2.5: 智能追问 ============
    <div className="wizard upload-step">
      <h2>我看完了你们的聊天记录</h2>
      <p className="sub">有几个地方还不太确定，想请你帮我理一理</p>

      {questions.map((q, i) => (
        <div key={i} style={{ marginBottom: 20, background: '#fff', borderRadius: 10, padding: 14, boxShadow: '0 1px 2px rgba(0,0,0,0.04)' }}>
          <p style={{ color: '#5c4f3e', fontSize: '13px', marginBottom: 8 }}>
            {q.context_hint || `「${q.entity}」是什么？`}
          </p>
          {getChipsForType(q.type).length > 0 && (
            <div className="chips" style={{ marginBottom: 8 }}>
              {getChipsForType(q.type).map(chip => (
                <button
                  key={chip}
                  type="button"
                  className={`chip ${(q as any).selected_type === chip ? 'active' : ''}`}
                  onClick={() => updateAnswer(i, { type: chip, ...{selected_type: chip} } as any)}
                >
                  {chip}
                </button>
              ))}
            </div>
          )}
          <input
            value={q.detail}
            onChange={e => updateAnswer(i, { detail: e.target.value })}
            placeholder="还有什么想补充的吗？（不答也行）"
            style={{ width: '100%', padding: '10px 12px', border: '1px solid var(--border)', borderRadius: 8, fontSize: 13, fontFamily: 'inherit' }}
          />
        </div>
      ))}

      <p style={{ color: '#b8a898', fontSize: '11px', textAlign: 'center', marginBottom: 16 }}>不想答就跳过，不影响后面的聊天</p>
      {error && <p className="error-msg">{error}</p>}
      <button className="btn-primary" onClick={submitAnswersAndContinue}>好了，开始整理回忆 →</button>
    </div>
  );
}
```

- [ ] **Step 2: Build to verify**

```bash
cd D:\重逢2 && npm run build
```
Expected: build passes.

- [ ] **Step 3: Commit**

```bash
cd D:\重逢2 && git add src/components/Wizard.tsx && git commit -m "feat: 5-screen wizard with guided onboarding + smart questions"
```

---

### Task 6: Frontend — App.tsx integration

**Files:**
- Modify: `src/App.tsx`

- [ ] **Step 1: Update App.tsx**

Replace the entire file:

```tsx
import React, { useEffect, useState } from 'react';
import { useSetup } from './hooks/useSetup';
import { Wizard } from './components/Wizard';
import { ChatWindow } from './components/ChatWindow';
import { SettingsPanel } from './components/SettingsPanel';
import { getSettings } from './api';
import type { Config } from './types';

export default function App() {
  const {
    step, error, loading, backendReady, init,
    setupData, questions,
    submit1a, submit1b, submit1c, submitUpload,
    submitAnswersAndContinue, updateAnswer, goBack,
  } = useSetup();
  const [showSettings, setShowSettings] = useState(false);
  const [config, setConfig] = useState<Config | null>(null);

  useEffect(() => { init(); }, [init]);

  useEffect(() => {
    if (backendReady) {
      getSettings().then(c => setConfig(c)).catch(() => {});
    }
  }, [backendReady]);

  if (!backendReady) {
    return (
      <div className="app-loading">
        <div className="spinner" />
        <p>正在启动…</p>
        {error && <p className="error-msg">{error}</p>}
      </div>
    );
  }

  const isWizard = step !== 'chat';

  return (
    <div className="app">
      {isWizard ? (
        <Wizard
          step={step}
          error={error}
          loading={loading}
          setupData={setupData}
          questions={questions}
          submit1a={submit1a}
          submit1b={submit1b}
          submit1c={submit1c}
          submitUpload={submitUpload}
          submitAnswersAndContinue={submitAnswersAndContinue}
          updateAnswer={updateAnswer}
          onBack={goBack}
        />
      ) : (
        <ChatWindow onSettingsClick={() => setShowSettings(true)} />
      )}
      {showSettings && <SettingsPanel onClose={() => setShowSettings(false)} />}
    </div>
  );
}
```

- [ ] **Step 2: Build**

```bash
cd D:\重逢2 && npm run build
```
Expected: `✓ 35 modules transformed.`

- [ ] **Step 3: Commit**

```bash
cd D:\重逢2 && git add src/App.tsx && git commit -m "feat: integrate guided onboarding wizard into App"
```

---

## Summary

**6 tasks, 7 files modified.** Frontend flow goes from 2 screens (soul + upload) to 5 screens (1a + 1b + 1c + upload + smart-questions). Backend gains entity extraction via LLM and answer merge into persona.

**Testing:** After all tasks, run `npm run electron:dev` and walk through full flow — fill 1a/1b/1c, upload chat log, see smart questions, answer them, enter chat.
