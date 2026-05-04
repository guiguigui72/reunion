export interface Config {
  api_key: string;
  name: string;
  your_name: string;
  relationship: string;
  personality: string;
  extra: string;
  has_avatar: boolean;
}

export interface Message {
  role: 'user' | 'assistant';
  content: string;
}

export interface SetupRequest {
  api_key: string;
  name: string;
  your_name: string;
  relationship: string;
  personality: string;
  extra: string;
  chat_log: string;
}

export interface SetupResponse {
  status: string;
  message: string;
  has_persona: boolean;
}

export interface ChatResponse {
  reply: string;
  history: Message[];
}

export type AppStep = 'soul' | 'upload' | 'processing' | 'chat';
