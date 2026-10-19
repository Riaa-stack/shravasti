import { create } from 'zustand';

export interface Paper {
  id: string;
  title: string;
  authors?: string[] | string;
  abstract?: string;
  category?: string;
  publication_year?: number;
  venue?: string;
  doi?: string;
  file_path?: string;
  status: 'uploaded' | 'processing' | 'processed' | 'failed';
  upload_date?: string;
  created_at?: string;
  difficulty_level?: 'easy' | 'medium' | 'hard';
  is_flagged?: boolean;
  flag_reason?: string | null;
  is_available_for_ai?: boolean;
  user_id?: string;
  user_name?: string;
  user_email?: string;
  user_role?: string;
}

interface PaperState {
  papers: Paper[];
  selectedPaperIds: string[];
  setPapers: (papers: Paper[]) => void;
  addPaper: (paper: Paper) => void;
  updatePaper: (id: string, updates: Partial<Paper>) => void;
  toggleSelection: (id: string) => void;
  clearSelection: () => void;
  selectAll: () => void;
  setSelectedPaperIds: (ids: string[]) => void;
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
  selectAll: () => set((state) => ({ selectedPaperIds: state.papers.map(p => p.id) })),
  setSelectedPaperIds: (ids) => set({ selectedPaperIds: ids }),
}));
