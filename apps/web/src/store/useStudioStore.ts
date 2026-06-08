import { create } from 'zustand';

export type PageKey = 'dashboard' | 'projects' | 'novel' | 'workbench' | 'models';

interface StudioState {
  page: PageKey;
  activeProjectId: number;
  activeNovelId: number;
  activeChapterId: number;
  activeChapterNumber: number;
  error: string;
  setPage: (page: PageKey) => void;
  selectProject: (id: number) => void;
  selectNovel: (id: number) => void;
  selectChapter: (id: number, chapterNumber: number) => void;
  clearSelection: () => void;
  setError: (message: string) => void;
  clearError: () => void;
}

export const useStudioStore = create<StudioState>((set) => ({
  page: 'dashboard',
  activeProjectId: 0,
  activeNovelId: 0,
  activeChapterId: 0,
  activeChapterNumber: 1,
  error: '',
  setPage: (page) => set({ page }),
  selectProject: (id) => set({ activeProjectId: id, activeNovelId: 0, activeChapterId: 0, page: 'novel' }),
  selectNovel: (id) => set({ activeNovelId: id, activeChapterId: 0, activeChapterNumber: 1, page: 'workbench' }),
  selectChapter: (id, chapterNumber) => set({ activeChapterId: id, activeChapterNumber: chapterNumber }),
  clearSelection: () => set({ activeProjectId: 0, activeNovelId: 0, activeChapterId: 0, activeChapterNumber: 1 }),
  setError: (message) => set({ error: message }),
  clearError: () => set({ error: '' }),
}));
