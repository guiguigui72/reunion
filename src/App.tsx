import React, { useEffect, useState } from 'react';
import { useSetup } from './hooks/useSetup';
import { Wizard } from './components/Wizard';
import { ChatWindow } from './components/ChatWindow';
import { SettingsPanel } from './components/SettingsPanel';
import { getSettings } from './api';
import type { Config } from './types';

export default function App() {
  const { step, error, loading, backendReady, init, submitSoul, submitUpload } = useSetup();
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

  return (
    <div className="app">
      {step !== 'chat' ? (
        <Wizard step={step} error={error} loading={loading} onSubmitSoul={submitSoul} onSubmitUpload={submitUpload} />
      ) : (
        <ChatWindow onSettingsClick={() => setShowSettings(true)} />
      )}
      {showSettings && <SettingsPanel onClose={() => setShowSettings(false)} />}
    </div>
  );
}
