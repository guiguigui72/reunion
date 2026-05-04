import { useState, useCallback } from 'react';
import type { AppStep, SetupRequest } from '../types';
import { runSetup, initBackend, healthCheck } from '../api';

export function useSetup() {
  const [step, setStep] = useState<AppStep>('soul');
  const [error, setError] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [backendReady, setBackendReady] = useState(false);

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

  const submitSoul = useCallback((_data: Partial<SetupRequest>) => {
    setStep('upload');
  }, []);

  const submitUpload = useCallback(async (data: SetupRequest) => {
    setStep('processing');
    setError('');
    setLoading(true);
    try {
      await runSetup(data);
      setStep('chat');
    } catch (e: any) {
      setError(e.message || '处理失败，请重试');
      setStep('upload');
    } finally {
      setLoading(false);
    }
  }, []);

  return { step, setStep, error, loading, backendReady, init, submitSoul, submitUpload };
}
