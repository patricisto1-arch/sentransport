import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';
import type { Langue, Theme } from '@/api/types';

export interface NotificationApp {
  id: string;
  titre: string;
  texte: string;
  date: string;
  lu: boolean;
  ton: 'accent' | 'success' | 'warning' | 'info';
  href?: string;
}

interface UIState {
  theme: Theme;
  langue: Langue;
  sidebarMobile: boolean;
  paletteOuverte: boolean;
  notificationsOuvertes: boolean;
  notifications: NotificationApp[];
  setTheme: (theme: Theme) => void;
  toggleTheme: () => void;
  setLangue: (langue: Langue) => void;
  setSidebarMobile: (ouvert: boolean) => void;
  setPaletteOuverte: (ouvert: boolean) => void;
  setNotificationsOuvertes: (ouvert: boolean) => void;
  marquerLu: (id: string) => void;
  marquerToutLu: () => void;
  ajouterNotification: (notification: Omit<NotificationApp, 'id' | 'date' | 'lu'>) => void;
}

const notificationsInitiales: NotificationApp[] = [];

function appliquerTheme(theme: Theme) {
  if (typeof document === 'undefined') return;
  document.documentElement.classList.toggle('dark', theme === 'dark');
  document
    .querySelector('meta[name="theme-color"]')
    ?.setAttribute('content', theme === 'dark' ? '#0F0D1A' : '#D9D3F5');
}

export const useUIStore = create<UIState>()(
  persist(
    (set, get) => ({
      theme: 'light',
      langue: 'fr',
      sidebarMobile: false,
      paletteOuverte: false,
      notificationsOuvertes: false,
      notifications: notificationsInitiales,
      setTheme: (theme) => {
        appliquerTheme(theme);
        set({ theme });
      },
      toggleTheme: () => get().setTheme(get().theme === 'dark' ? 'light' : 'dark'),
      setLangue: (langue) => set({ langue }),
      setSidebarMobile: (sidebarMobile) => set({ sidebarMobile }),
      setPaletteOuverte: (paletteOuverte) => set({ paletteOuverte }),
      setNotificationsOuvertes: (notificationsOuvertes) =>
        set({ notificationsOuvertes }),
      marquerLu: (id) =>
        set((state) => ({
          notifications: state.notifications.map((n) =>
            n.id === id ? { ...n, lu: true } : n,
          ),
        })),
      marquerToutLu: () =>
        set((state) => ({
          notifications: state.notifications.map((n) => ({ ...n, lu: true })),
        })),
      ajouterNotification: (notification) =>
        set((state) => ({
          notifications: [
            {
              ...notification,
              id: `n-${Date.now()}`,
              date: new Date().toISOString(),
              lu: false,
            },
            ...state.notifications,
          ].slice(0, 40),
        })),
    }),
    {
      name: 'st.ui',
      version: 2,
      // v2 : on supprime les notifications de démonstration enregistrées par l'ancienne version.
      migrate: (etat) => ({ ...(etat as Partial<UIState>), notifications: [] }) as UIState,
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        theme: state.theme,
        langue: state.langue,
        notifications: state.notifications,
      }),
      onRehydrateStorage: () => (state) => {
        if (state) appliquerTheme(state.theme);
      },
    },
  ),
);

/** Initialise le thème avant le premier rendu (évite un flash clair). */
export function initialiserTheme() {
  const stocke = useUIStore.getState().theme;
  const systeme = window.matchMedia?.('(prefers-color-scheme: dark)').matches
    ? 'dark'
    : 'light';
  const theme = stocke ?? systeme;
  appliquerTheme(theme);
  if (theme !== stocke) useUIStore.getState().setTheme(theme);
}
