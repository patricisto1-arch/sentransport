import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { App } from './App';
import { initialiserTheme } from './store/ui';
import './styles/globals.css';

async function demarrer() {
  initialiserTheme();

  const mocksActifs =
    import.meta.env.VITE_USE_MOCKS === 'true' ||
    (import.meta.env.DEV && import.meta.env.VITE_USE_MOCKS !== 'false');

  if (mocksActifs) {
    try {
      const { activerMocks } = await import('./mocks/browser');
      await activerMocks();
    } catch (erreur) {
      console.error('MSW n’a pas pu démarrer :', erreur);
    }
  }

  const racine = document.getElementById('root');
  if (!racine) throw new Error('Élément #root introuvable');

  createRoot(racine).render(
    <StrictMode>
      <App />
    </StrictMode>,
  );
}

void demarrer();
