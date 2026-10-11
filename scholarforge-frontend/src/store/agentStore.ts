import { create } from 'zustand';

interface AgentResultCache {
  batchKey: string;
  result: any;
}

interface AgentStoreState {
  cachedResults: Record<string, AgentResultCache>;
  setAgentResult: (endpoint: string, batchKey: string, result: any) => void;
  getAgentResult: (endpoint: string, batchKey: string) => any;
  clearResults: () => void;
}

export const useAgentStore = create<AgentStoreState>((set, get) => ({
  cachedResults: {},
  setAgentResult: (endpoint, batchKey, result) => {
    set((state) => ({
      cachedResults: {
        ...state.cachedResults,
        [endpoint]: { batchKey, result },
      },
    }));
  },
  getAgentResult: (endpoint, batchKey) => {
    const entry = get().cachedResults[endpoint];
    if (entry && entry.batchKey === batchKey) {
      return entry.result;
    }
    return null;
  },
  clearResults: () => set({ cachedResults: {} }),
}));
