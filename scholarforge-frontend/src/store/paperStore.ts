import { create } from 'zustand';

export interface Paper {
  id: string;
  title: string;
  authors: string;
  abstract: string;
  status: 'uploaded' | 'processing' | 'processed' | 'failed';
  upload_date: string;
  difficulty_level?: 'easy' | 'medium' | 'hard';
}

interface PaperState {
  papers: Paper[];
  selectedPaperIds: string[];
  setPapers: (papers: Paper[]) => void;
  addPaper: (paper: Paper) => void;
  updatePaper: (id: string, updates: Partial<Paper>) => void;
  toggleSelection: (id: string) => void;
  clearSelection: () => void;
}

export const usePaperStore = create<PaperState>((set) => ({
  papers: [],
  selectedPaperIds: [],
  setPapers: (papers) => set({ papers }),
  addPaper: (paper) => set((state) => ({ papers: [paper, ...state.papers] })),
  updatePaper: (id, updates) => set((state) => ({
    papers: state.papers.map(p => p.id === id ? { ...p, ...updates } : p)
  })),
  toggleSelection: (id) => set((state) => ({
    selectedPaperIds: state.selectedPaperIds.includes(id)
      ? state.selectedPaperIds.filter(pid => pid !== id)
      : [...state.selectedPaperIds, id]
  })),
  clearSelection: () => set({ selectedPaperIds: [] }),
}));
