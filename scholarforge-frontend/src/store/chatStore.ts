import { create } from 'zustand';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: string[];
}

interface ChatState {
  messages: ChatMessage[];
  isTyping: boolean;
  addMessage: (message: ChatMessage) => void;
  appendToken: (messageId: string, token: string) => void;
  setTyping: (isTyping: boolean) => void;
  clearMessages: () => void;
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  isTyping: false,
  addMessage: (message) => set((state) => ({ messages: [...state.messages, message] })),
  appendToken: (messageId, token) => set((state) => ({
    messages: state.messages.map(m => 
      m.id === messageId ? { ...m, content: m.content + token } : m
    )
  })),
  setTyping: (isTyping) => set({ isTyping }),
  clearMessages: () => set({ messages: [] })
}));
