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
          <input type="text" value={name} onChange={e => setName(e.target.value)} placeholder="妈妈、外婆、阿杰…" required />

          <label>他平时怎么叫你？</label>
          <input type="text" value={yourName} onChange={e => setYourName(e.target.value)} placeholder="小宝、囡囡、或者你的名字…" />

          <label>你们的关系</label>
          <div className="chips">
            {RELATIONSHIPS.map(r => (
              <button key={r} type="button" className={`chip ${relationship === r ? 'active' : ''}`} onClick={() => setRelationship(r)}>{r}</button>
            ))}
          </div>

          <label>上次见到他，是什么时候的事了？</label>
          <input type="text" value={lastSeen} onChange={e => setLastSeen(e.target.value)} placeholder="一年多了、上个月、记不太清了…" />

          <div className="row">
            <div>
              <label>他是哪一年出生的？</label>
              <input type="text" value={birthYear} onChange={e => setBirthYear(e.target.value)} placeholder="1968 年、属猴的…" />
            </div>
            <div>
              <label>他的星座和 MBTI？</label>
              <input type="text" value={zodiac} onChange={e => setZodiac(e.target.value)} placeholder="不记得也没关系" />
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
          <input type="text" value={habit} onChange={e => setHabit(e.target.value)} placeholder="爱说「你看看你」、出门前总要折回来一次…" />

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
