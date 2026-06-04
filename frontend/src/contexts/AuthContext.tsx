//frontend/src/contexts/AuthContext.tsx
import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  useCallback,
  type ReactNode
} from 'react';
import {
  User,
  createUserWithEmailAndPassword,
  signInWithEmailAndPassword,
  signInWithPopup,
  signInWithRedirect,
  signOut as firebaseSignOut,
  onIdTokenChanged,
  getRedirectResult
} from 'firebase/auth';
import { auth, firebaseConfigError, googleProvider } from '../firebase';

interface AuthContextType {
  user: User | null;
  token: string | null;
  loading: boolean;
  configError: string | null;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  loginWithGoogle: () => Promise<User>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

    const logout = useCallback(async () => {
  if (!auth) {
    localStorage.removeItem('authToken');
    setUser(null);
    setToken(null);
    return;
  }

  await firebaseSignOut(auth);
  localStorage.removeItem('authToken');
  setUser(null);
  setToken(null);
  }, []);


  useEffect(() => {
    if (!auth) {
      setLoading(false);
      return;
    }

    // If user came back from a redirect-based sign-in, finalize it.
    void getRedirectResult(auth).catch(() => {
      // ignore; onIdTokenChanged will handle the signed-in state
    });

    const unsubscribe = onIdTokenChanged(auth, async (firebaseUser) => {
      if (firebaseUser) {
        const idToken = await firebaseUser.getIdToken();
        localStorage.setItem('authToken', idToken);
        setUser(firebaseUser);
        setToken(idToken);
        window.dispatchEvent(
          new CustomEvent('auth:token-refresh', {
            detail: idToken,
          })
        );
      } else {
        localStorage.removeItem('authToken');
        setUser(null);
        setToken(null);
      }
      setLoading(false);
    });

    return unsubscribe;
  }, []);

  useEffect(() => {
    if (!user || !auth) {
      return;
    }

    const currentAuth = auth;
    const interval = window.setInterval(async () => {
      if (currentAuth.currentUser) {
        const idToken = await currentAuth.currentUser.getIdToken(true);
        localStorage.setItem('authToken', idToken);
        setToken(idToken);
        window.dispatchEvent(
          new CustomEvent('auth:token-refresh', {
            detail: idToken,
          })
        );
      }
    }, 50 * 60 * 1000);

    return () => window.clearInterval(interval);
  }, [user]);

  useEffect(() => {
    const handleLogoutEvent = () => {
      void logout();
    };

    window.addEventListener('auth:logout', handleLogoutEvent);
    return () => window.removeEventListener('auth:logout', handleLogoutEvent);
  }, [logout]);

  const login = async (email: string, password: string) => {
    if (!auth) {
      throw new Error(firebaseConfigError ?? 'Firebase authentication is not configured.');
    }

    const credentials = await signInWithEmailAndPassword(auth, email, password);
    const idToken = await credentials.user.getIdToken();
    localStorage.setItem('authToken', idToken);
    setUser(credentials.user);
    setToken(idToken);
    window.dispatchEvent(
      new CustomEvent('auth:token-refresh', {
        detail: idToken,
      })
    );
  };

  const register = async (email: string, password: string) => {
    if (!auth) {
      throw new Error(firebaseConfigError ?? 'Firebase authentication is not configured.');
    }

    const credentials = await createUserWithEmailAndPassword(auth, email, password);
    const idToken = await credentials.user.getIdToken();
    localStorage.setItem('authToken', idToken);
    setUser(credentials.user);
    setToken(idToken);
    window.dispatchEvent(
      new CustomEvent('auth:token-refresh', {
        detail: idToken,
      })
    );
  };

  const loginWithGoogle = async () => {
    if (!auth || !googleProvider) {
      throw new Error(firebaseConfigError ?? 'Firebase authentication is not configured.');
    }

    try {
      const credentials = await signInWithPopup(auth, googleProvider);
      const idToken = await credentials.user.getIdToken();
      localStorage.setItem('authToken', idToken);
      setUser(credentials.user);
      setToken(idToken);
      window.dispatchEvent(
        new CustomEvent('auth:token-refresh', {
          detail: idToken,
        })
      );
      return credentials.user;
    } catch (err: any) {
      if (err?.code === 'auth/unauthorized-domain') {
        const host = window.location.hostname;
        throw new Error(
          `Google sign-in is not enabled for ${host}. Use http://localhost:5173 or add ${host} in Firebase Authentication > Settings > Authorized domains.`,
        );
      }

      // On mobile/webview/network conditions, popup-based flow often fails.
      // Fallback to redirect-based flow (onIdTokenChanged will complete the session).
      await signInWithRedirect(auth, googleProvider);
      // Redirect will reload the page; returning a value here isn't guaranteed.
      throw err;
    }
  };


  const value = useMemo(
    () => ({ user, token, loading, configError: firebaseConfigError, login, register, loginWithGoogle, logout }),
    [user, token, loading]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used inside AuthProvider');
  }
  return context;
}
