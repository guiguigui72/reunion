import React, { useEffect, useState } from 'react';
import { MessageBubble } from './MessageBubble';
import { useChat } from '../hooks/useChat';
import { getSettings, getAvatarUrl } from '../api';

interface Props { onSettingsClick: () => void; }

export function ChatWindow({ onSettingsClick }: Props) {
  const { messages, isTyping, error, send, loadHistory, messagesEndRef } = useChat();
  const [input, setInput] = useState('');
  const [aiName, setAiName] = useState('');
  const [hasAvatar, setHasAvatar] = useState(false);
  const [avatarUrl, setAvatarUrl] = useState('');
  const isFirstChat = messages.length === 0;

  useEffect(() => {
    loadHistory();
    getSettings().then(c => {
      setAiName(c.name || '');
      setHasAvatar(c.has_avatar);
      if (c.has_avatar) setAvatarUrl(getAvatarUrl());
    }).catch(() => {});
  }, [loadHistory]);

  const handleSend = () => { if (!input.trim()) return; send(input); setInput(''); };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
  };

  return (
    <div className="chat-window">
      <div className="chat-header">
        <div className="header-left">
          <div
            className="avatar ai-avatar small"
            style={hasAvatar ? {
              backgroundImage: `url(${avatarUrl})`,
              backgroundSize: 'cover',
              backgroundPosition: 'center',
            } : {}}
          />
          <span className="header-name">{aiName || '重逢'}</span>
        </div>
        <button className="gear-btn" onClick={onSettingsClick}>&#9881;</button>
      </div>
      <div className="chat-messages">
        {isFirstChat && <div className="first-chat-banner">这是你们重逢的开始</div>}
        {messages.map((msg, i) => (
          <MessageBubble
            key={i}
            message={msg}
            aiName={aiName}
            hasAvatar={hasAvatar}
            avatarUrl={avatarUrl}
          />
        ))}
        {isTyping && <div className="typing-indicator">对方正在输入...</div>}
        {error && <div className="error-msg">{error}</div>}
        <div ref={messagesEndRef} />
      </div>
      <div className="chat-input-bar">
        <input value={input} onChange={e => setInput(e.target.value)} onKeyDown={handleKeyDown} placeholder="说点什么吧…" />
        <button onClick={handleSend} className="btn-send">发送</button>
      </div>
    </div>
  );
}
