import type { Config, SetupRequest, SetupResponse, ChatResponse, Message, AnswerItem } from './types';

let BASE_URL = '';

export async function initBackend(): Promise<void> {
  if (window.electronAPI) {
    const port = await window.electronAPI.getBackendPort();
    BASE_URL = `http://127.0.0.1:${port}`;
  } else {
    BASE_URL = 'http://127.0.0.1:8000';
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Request failed');
  }
  return res.json();
}

export function healthCheck(): Promise<{ status: string }> {
  return request('/api/health');
}

export function runSetup(data: SetupRequest): Promise<SetupResponse> {
  return request('/api/setup', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export function sendMessage(message: string): Promise<ChatResponse> {
  return request('/api/chat', {
    method: 'POST',
    body: JSON.stringify({ message }),
  });
}

export function getHistory(): Promise<{ history: Message[] }> {
  return request('/api/chat/history');
}

export function getSettings(): Promise<Config> {
  return request('/api/settings');
}

export function updateSettings(data: Partial<Config>): Promise<{ status: string }> {
  return request('/api/settings', {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export function resetAll(): Promise<{ status: string }> {
  return request('/api/settings/reset', {
    method: 'DELETE',
  });
}

export async function uploadAvatar(file: File): Promise<void> {
  const formData = new FormData();
  formData.append('file', file);
  const res = await fetch(`${BASE_URL}/api/settings/avatar`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Upload failed');
  }
}

export function getAvatarUrl(): string {
  return `${BASE_URL}/api/settings/avatar`;
}

export async function submitAnswers(apiKey: string, answers: AnswerItem[]): Promise<void> {
  await request('/api/setup/answers', {
    method: 'POST',
    body: JSON.stringify({ api_key: apiKey, answers }),
  });
}
