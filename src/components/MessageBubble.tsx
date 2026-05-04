import React from 'react';
import type { Message } from '../types';

interface Props { message: Message; aiName: string; }

export function MessageBubble({ message, aiName }: Props) {
  const isUser = message.role === 'user';
  return (
    <div className={`message-row ${isUser ? 'user' : 'ai'}`}>
      {!isUser && <div className="avatar ai-avatar" />}
      <div className={`bubble ${isUser ? 'user-bubble' : 'ai-bubble'}`}>{message.content}</div>
      {isUser && <div className="avatar user-avatar" />}
    </div>
  );
}
