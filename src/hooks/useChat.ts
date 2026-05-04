import { useState, useCallback, useRef } from 'react';
import type { Message } from '../types';
import { sendMessage, getHistory } from '../api';

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isTyping, setIsTyping] = useState(false);
  const [error, setError] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const loadHistory = useCallback(async () => {
    try { const data = await getHistory(); setMessages(data.history); } catch {}
  }, []);

  const send = useCallback(async (text: string) => {
    if (!text.trim()) return;
    setError('');
    const userMsg: Message = { role: 'user', content: text };
    setMessages(prev => [...prev, userMsg]);
    setIsTyping(true);
    try {
      const res = await sendMessage(text);
      setMessages(prev => [...prev, { role: 'assistant', content: res.reply }]);
    } catch (e: any) {
      setError(e.message || '发送失败');
    } finally {
      setIsTyping(false);
    }
  }, []);

  return { messages, isTyping, error, send, loadHistory, messagesEndRef };
}
