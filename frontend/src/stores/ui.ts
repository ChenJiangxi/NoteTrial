import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { Content, ABTest, Post } from '@/types';

// UI State Store
interface UIState {
  sidebarOpen: boolean;
  theme: 'light' | 'dark';
  toggleSidebar: () => void;
  setTheme: (theme: 'light' | 'dark') => void;
}

export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      sidebarOpen: true,
      theme: 'light',
      toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
      setTheme: (theme) => set({ theme }),
    }),
    {
      name: 'notetrial-ui',
    }
  )
);

// Recent Items Store
interface RecentItemsState {
  recentContents: Content[];
  recentTests: ABTest[];
  addRecentContent: (content: Content) => void;
  addRecentTest: (test: ABTest) => void;
  clearRecent: () => void;
}

export const useRecentItemsStore = create<RecentItemsState>()(
  persist(
    (set, get) => ({
      recentContents: [],
      recentTests: [],
      
      addRecentContent: (content) =>
        set((state) => ({
          recentContents: [
            content,
            ...state.recentContents.filter((c) => c.id !== content.id).slice(0, 9),
          ],
        })),
      
      addRecentTest: (test) =>
        set((state) => ({
          recentTests: [
            test,
            ...state.recentTests.filter((t) => t.id !== test.id).slice(0, 9),
          ],
        })),
      
      clearRecent: () => set({ recentContents: [], recentTests: [] }),
    }),
    {
      name: 'notetrial-recent',
    }
  )
);

// Editor State Store
interface EditorState {
  currentContent: Content | null;
  editMode: 'create' | 'edit' | 'ab-test';
  setCurrentContent: (content: Content | null) => void;
  setEditMode: (mode: 'create' | 'edit' | 'ab-test') => void;
  reset: () => void;
}

export const useEditorStore = create<EditorState>()((set) => ({
  currentContent: null,
  editMode: 'create',
  
  setCurrentContent: (content) => set({ currentContent: content }),
  setEditMode: (mode) => set({ editMode: mode }),
  reset: () => set({ currentContent: null, editMode: 'create' }),
}));
