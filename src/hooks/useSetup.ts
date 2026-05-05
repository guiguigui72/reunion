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
