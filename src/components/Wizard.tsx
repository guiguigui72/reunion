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
    reader.onload = () => setChatLog(reader.result as string);
    reader.readAsText(file);
  };

  const handleUploadSubmit = () => {
    onSubmitUpload({ api_key: apiKey, name, your_name: yourName, relationship, personality, extra, chat_log: chatLog });
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
        <div className="avatar-upload">
          <div className="avatar-circle">设置<br/>头像</div>
          <span className="avatar-hint">设置他的头像（可选）</span>
        </div>
        <form onSubmit={handleSoulSubmit}>
          <label>DeepSeek API Key</label>
          <input type="password" value={apiKey} onChange={e => setApiKey(e.target.value)} placeholder="sk-..." required />
          <div className="row">
            <div>
              <label>你对他的称呼</label>
              <input value={name} onChange={e => setName(e.target.value)} placeholder="例如：妈妈" required />
            </div>
            <div>
              <label>他叫你的名字</label>
              <input value={yourName} onChange={e => setYourName(e.target.value)} placeholder="例如：小宝" />
            </div>
          </div>
          <label>你们的关系</label>
          <div className="chips">
            {RELATIONSHIPS.map(r => (
              <button key={r} type="button" className={`chip ${relationship === r ? 'active' : ''}`} onClick={() => setRelationship(r)}>{r}</button>
            ))}
          </div>
          <label>他的性格特点</label>
          <textarea value={personality} onChange={e => setPersonality(e.target.value)} placeholder="描述他的说话方式和性格…" rows={3} />
          <label>关于他，你还想告诉我的</label>
          <textarea value={extra} onChange={e => setExtra(e.target.value)} placeholder="口头禅、你们的共同记忆、他对你的态度…" rows={2} />
          <button type="submit" className="btn-primary">下一步 →</button>
        </form>
      </div>
    );
  }

  return (
    <div className="wizard upload-step">
      <h2>加载记忆</h2>
      <p className="sub">上传你与他的聊天记录，越完整越好，时间跨度越长他越像本人</p>
      <div className="drop-zone" onClick={() => fileInputRef.current?.click()}>
        {chatLog ? <p>已选择文件（{chatLog.length.toLocaleString()} 字）</p> : <><p>拖拽 TXT 文件到这里，或点击选择</p><p className="hint">支持微信 / QQ 导出的聊天记录文件</p></>}
      </div>
      <input ref={fileInputRef} type="file" accept=".txt" onChange={handleFileChange} style={{ display: 'none' }} />
      {error && <p className="error-msg">{error}</p>}
      <button className="btn-primary" onClick={handleUploadSubmit}>开始整理回忆</button>
    </div>
  );
}
