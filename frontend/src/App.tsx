//src/App.tsx

import React, { Suspense } from 'react';
import { Navigate, Route, Routes, useLocation } from 'react-router-dom';
import { useTheme } from './ui/theme';
import { SpeedInsights } from '@vercel/speed-insights/react';
const Dashboard = React.lazy(() => import('./pages/Dashboard'));
const Landing = React.lazy(() => import('./pages/Landing'));
const Feed = React.lazy(() => import('./pages/Feed'));
const Chat = React.lazy(() => import('./pages/Chat'));
const Groups = React.lazy(() => import('./pages/Groups'));
const Search = React.lazy(() => import('./pages/Search'));
const Friends = React.lazy(() => import('./pages/Friends'));
const Login = React.lazy(() => import('./features/auth/Login'));
const Profile = React.lazy(() => import('./pages/Profile'));
const Register = React.lazy(() => import('./features/auth/Register'));
const Onboarding = React.lazy(() => import('./features/auth/Onboarding'));
const NotFound = React.lazy(() => import('./pages/NotFound'));
const Unauthorized = React.lazy(() => import('./pages/Unauthorized'));
const AdminDashboard = React.lazy(() => import('./features/admin/AdminDashboard'));
import Sidebar from './layout/Sidebar';
import Topbar from './layout/Topbar';
import RightSidebar from './layout/RightSidebar';
import BottomNav from './layout/BottomNav';
import OfflineStatus from './components/OfflineStatus';
import './styles/layout.css';
import ProtectedRoute from './components/ProtectedRoute';
import { useAuth } from './contexts/AuthContext';
import { useSwipeNavigation } from './hooks/useSwipeNavigation';
import { useToasts } from './ui/ToastProvider';

type BeforeInstallPromptEvent = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed'; platform: string }>;
};

function App() {
  const { theme } = useTheme();
  const { user, loading } = useAuth();
  const location = useLocation();
  const { push } = useToasts();
  const [installPrompt, setInstallPrompt] = React.useState<BeforeInstallPromptEvent | null>(null);
  const [updateReady, setUpdateReady] = React.useState(false);

  const themeClass = theme === 'dark' ? 'theme-dark' : 'theme-light';
  const busyState = loading ? 'true' : 'false';

  React.useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      void import('./pages/Feed');
      void import('./pages/Chat');
      void import('./pages/Groups');
      void import('./pages/Profile');
      void import('./pages/Search');
      void import('./pages/Friends');
    }, 1200);
    return () => window.clearTimeout(timeoutId);
  }, []);

  React.useEffect(() => {
    const installHandler = (event: Event) => {
      event.preventDefault();
      setInstallPrompt(event as BeforeInstallPromptEvent);
    };

    const updateHandler = () => setUpdateReady(true);
    const installedHandler = () => {
      push({ type: 'success', message: 'ChattingApp installed. Offline support is ready.' });
      setInstallPrompt(null);
    };

    window.addEventListener('beforeinstallprompt', installHandler as EventListener);
    window.addEventListener('pwa:update-ready', updateHandler);
    window.addEventListener('appinstalled', installedHandler);

    return () => {
      window.removeEventListener('beforeinstallprompt', installHandler as EventListener);
      window.removeEventListener('pwa:update-ready', updateHandler);
      window.removeEventListener('appinstalled', installedHandler);
    };
  }, [push]);

  const installApp = async () => {
    if (!installPrompt) return;
    await installPrompt.prompt();
    const choiceResult = await installPrompt.userChoice;
    if (choiceResult.outcome === 'accepted') {
      push({ type: 'success', message: 'Install accepted. Open ChattingApp from your home screen once ready.' });
    } else {
      push({ type: 'info', message: 'Install dismissed. You can install anytime from the browser menu.' });
    }
    setInstallPrompt(null);
  };

  const refreshForUpdate = async () => {
    const registration = await navigator.serviceWorker.getRegistration();
    if (registration?.waiting) {
      registration.waiting.postMessage({ type: 'SKIP_WAITING' });
    }
    window.location.reload();
  };

  const dismissPwaBanner = () => {
    setInstallPrompt(null);
    setUpdateReady(false);
  };

  const publicRoutes = ['/login', '/register'];
  const hideLayout = publicRoutes.includes(location.pathname) || (!user && location.pathname === '/');
  useSwipeNavigation(Boolean(user && !hideLayout && !loading));

  if (loading) {
    return <div className="page-loading">Loading authentication...</div>;
  }

  const shellClass = ['app-shell', themeClass, !hideLayout && user ? 'app-shell-authenticated' : 'app-shell-public']
    .filter(Boolean)
    .join(' ');

  return (
    <div className={shellClass} data-theme={theme}>
      <a className="skip-link" href="#main-content">Skip to content</a>
      <div className="background-grid" aria-hidden="true"></div>
      {!hideLayout && user && (
        <aside className="app-sidebar">
          <Sidebar />
        </aside>
      )}
      <main className="app-main" id="main-content" tabIndex={-1}>
        {!hideLayout && <Topbar />}
        {!hideLayout && <OfflineStatus />}
        {(installPrompt || updateReady) && !hideLayout && (
          <div className="pwa-banner" role="region" aria-live="polite">
            <div className="pwa-banner-copy">
              {updateReady
                ? 'A new version of ChattingApp is ready. Reload to update and keep offline content fresh.'
                : 'Install ChattingApp for faster launches, offline support, and app-like behavior.'}
            </div>
            <div className="pwa-banner-actions">
              {updateReady ? (
                <button className="secondary-button" type="button" onClick={refreshForUpdate}>
                  Reload
                </button>
              ) : (
                <button className="primary-button" type="button" onClick={installApp}>
                  Install
                </button>
              )}
              <button className="ghost-button" type="button" onClick={dismissPwaBanner}>
                Dismiss
              </button>
            </div>
          </div>
        )}
        <section className={`page-frame page-transition ${hideLayout ? 'auth-frame' : ''}`} aria-busy={busyState}>
          <Suspense fallback={<div className="page-loading">Loading...</div>}>
            <Routes>
              <Route path="/" element={user ? <ProtectedRoute><Dashboard /></ProtectedRoute> : <Landing />} />
              <Route path="/feed" element={<ProtectedRoute><Feed /></ProtectedRoute>} />
              <Route path="/chat" element={<ProtectedRoute><Chat /></ProtectedRoute>} />
              <Route path="/groups" element={<ProtectedRoute><Groups /></ProtectedRoute>} />
              <Route path="/search" element={<ProtectedRoute><Search /></ProtectedRoute>} />
              <Route path="/friends" element={<ProtectedRoute><Friends /></ProtectedRoute>} />
              <Route path="/profile" element={<ProtectedRoute><Profile /></ProtectedRoute>} />
              <Route path="/admin" element={<ProtectedRoute allowedRoles={['admin', 'moderator']}><AdminDashboard /></ProtectedRoute>} />
              <Route path="/login" element={user ? <Navigate to="/" replace /> : <Login />} />
              <Route path="/register" element={<Register />} />
              <Route path="/onboarding" element={<ProtectedRoute><Onboarding /></ProtectedRoute>} />
              <Route path="/unauthorized" element={<Unauthorized />} />
              <Route path="*" element={<NotFound />} />
            </Routes>
          </Suspense>
        </section>
      </main>
      {!hideLayout && user && <RightSidebar />}
      {!hideLayout && user && <BottomNav />}
      <SpeedInsights />
    </div>
  );
}

export default App;
