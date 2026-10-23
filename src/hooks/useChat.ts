import { useState, useCallback, useRef } from 'react';
import type { Message } from '../types';
import { sendMessage, getHistory } from '../api';

// 回复太快时"正在输入"会闪一下，像故障；保证它至少可见这么久
const MIN_TYPING_MS = 600;

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
    const startedAt = Date.now();
    try {
      const res = await sendMessage(text);
      const elapsed = Date.now() - startedAt;
      if (elapsed < MIN_TYPING_MS) {
        await new Promise(r => setTimeout(r, MIN_TYPING_MS - elapsed));
      }
      setMessages(prev => [...prev, { role: 'assistant', content: res.reply }]);
    } catch (e: any) {
      setError(e.message || '发送失败');
    } finally {
      setIsTyping(false);
    }
  }, []);

  return { messages, isTyping, error, send, loadHistory, messagesEndRef };
}
