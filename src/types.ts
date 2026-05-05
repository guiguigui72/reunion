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

export interface Question {
  entity: string;
  context: string;
  type: 'pet' | 'person' | 'place' | 'object' | 'generic';
  context_hint: string;
}

export interface AnswerItem {
  entity: string;
  type: string;
  detail: string;
  context_hint: string;
}

export interface SetupResponse {
  status: string;
  message: string;
  has_persona: boolean;
  questions: Question[];
}

export interface ChatResponse {
  reply: string;
  history: Message[];
}

export type AppStep = 'guide_1a' | 'guide_1b' | 'guide_1c' | 'upload' | 'smart_questions' | 'processing' | 'chat';
