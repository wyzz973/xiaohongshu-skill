import { create } from 'zustand'

interface AppState {
  currentAccount: string
  sidebarCollapsed: boolean
  setCurrentAccount: (account: string) => void
  setSidebarCollapsed: (collapsed: boolean) => void
}

export const useAppStore = create<AppState>((set) => ({
  currentAccount: 'C',
  sidebarCollapsed: false,
  setCurrentAccount: (account) => set({ currentAccount: account }),
  setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),
}))
