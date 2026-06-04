import { Navigate } from 'react-router-dom';
import { useEffect, useMemo, useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { apiGetWithoutAuthLogout } from '../lib/api';
import { normalizeError } from '../lib/errors';

type ProtectedRouteProps = {
  children: JSX.Element;
  allowedRoles?: string[];
};

function ProtectedRoute({ children, allowedRoles = [] }: ProtectedRouteProps) {
  const { user, loading } = useAuth();
  const [authorization, setAuthorization] = useState<{
    loading: boolean;
    role: string | null;
    error: string | null;
  }>({ loading: false, role: null, error: null });
  const roleKey = useMemo(() => allowedRoles.join('|'), [allowedRoles]);

  useEffect(() => {
    let active = true;

    if (!roleKey || !user) {
      setAuthorization({ loading: false, role: null, error: null });
      return () => {
        active = false;
      };
    }

    setAuthorization({ loading: true, role: null, error: null });
    apiGetWithoutAuthLogout('/api/v1/users/me')
      .then((payload) => {
        if (!active) return;
        const profile = payload?.data ?? payload;
        setAuthorization({ loading: false, role: profile?.role ?? 'user', error: null });
      })
      .catch((err) => {
        if (!active) return;
        setAuthorization({
          loading: false,
          role: null,
          error: normalizeError(err, 'Could not verify access.').message,
        });
      });

    return () => {
      active = false;
    };
  }, [roleKey, user]);

  if (loading) {
    return <div className="page-loading">Checking authentication...</div>;
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (allowedRoles.length > 0) {
    if (authorization.loading || (!authorization.error && !authorization.role)) {
      return <div className="page-loading">Checking authorization...</div>;
    }

    if (authorization.error || !authorization.role || !allowedRoles.includes(authorization.role)) {
      return <Navigate to="/unauthorized" replace />;
    }
  }

  return children;
}

export default ProtectedRoute;
