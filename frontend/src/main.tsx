//src/main.tsx
import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import App from './App';
import { AuthProvider } from './contexts/AuthContext';
import { ThemeProvider } from './ui/theme';
import ToastProvider from './ui/ToastProvider';
import ErrorBoundary from './components/ErrorBoundary';
import './styles.css';
import { QueryClientProvider } from '@tanstack/react-query';
import { queryClient } from './lib/queryClient';
import { registerServiceWorker } from './lib/serviceWorker';
// Devtools: imported dynamically in dev to avoid production bundle bloat
let QueryDevtools: any = null;
if (import.meta.env.DEV) {
  // dynamic import is allowed in Vite; keep types loose
  import('@tanstack/react-query-devtools').then((mod) => {
    QueryDevtools = mod.ReactQueryDevtools;
  });
}

registerServiceWorker();

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <ThemeProvider>
      <ToastProvider>
        <QueryClientProvider client={queryClient}>
          <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
            <AuthProvider>
              <ErrorBoundary>
                <App />
              </ErrorBoundary>
            </AuthProvider>
          </BrowserRouter>
          {QueryDevtools ? <QueryDevtools initialIsOpen={false} /> : null}
        </QueryClientProvider>
      </ToastProvider>
    </ThemeProvider>
  </React.StrictMode>
);
