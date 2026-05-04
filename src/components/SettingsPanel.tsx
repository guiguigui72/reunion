import React, { useEffect, useState } from 'react';
import { getSettings, updateSettings, resetAll } from '../api';
import { DeleteConfirm } from './DeleteConfirm';
import type { Config } from '../types';

interface Props { onClose: () => void; }

const RELATIONSHIPS = ['父母', '伴侣', '子女', '朋友', '其他'];

export function SettingsPanel({ onClose }: Props) {
  const [config, setConfig] = useState<Config>({ api_key: '', name: '', your_name: '', relationship: '', personality: '', extra: '', has_avatar: false });
  const [showDelete, setShowDelete] = useState(false);

  useEffect(() => { getSettings().then(setConfig).catch(() => {}); }, []);

  const handleSave = async () => { await updateSettings(config); onClose(); };
  const handleDelete = async () => { await resetAll(); setShowDelete(false); onClose(); window.location.reload(); };

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
          <input type="password" value={config.api_key} onChange={e => setConfig({ ...config, api_key: e.target.value })} placeholder="sk-..." />
          <div className="row">
            <div><label>你对他的称呼</label><input value={config.name} onChange={e => setConfig({ ...config, name: e.target.value })} /></div>
            <div><label>他叫你的名字</label><input value={config.your_name} onChange={e => setConfig({ ...config, your_name: e.target.value })} /></div>
          </div>
          <label>你们的关系</label>
          <div className="chips">
            {RELATIONSHIPS.map(r => (
              <button key={r} type="button" className={`chip ${config.relationship === r ? 'active' : ''}`} onClick={() => setConfig({ ...config, relationship: r })}>{r}</button>
            ))}
          </div>
          <label>他的性格特点</label>
          <textarea value={config.personality} onChange={e => setConfig({ ...config, personality: e.target.value })} rows={3} />
          <label>关于他，你还想告诉我的</label>
          <textarea value={config.extra} onChange={e => setConfig({ ...config, extra: e.target.value })} rows={2} />
          <p className="update-hint">修改后会逐渐体现在对话中</p>
          <button className="btn-primary" onClick={handleSave}>保存修改</button>
          <div className="divider" />
          <div className="delete-section">
            <p>需要重新来过吗？</p>
            <button className="btn-delete" onClick={() => setShowDelete(true)}>删除并重新创建</button>
          </div>
        </div>
      </div>
      {showDelete && <DeleteConfirm onCancel={() => setShowDelete(false)} onConfirm={handleDelete} />}
    </div>
  );
}
