import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';

const useAuthMock = vi.fn();
const apiGetWithoutAuthLogoutMock = vi.fn();

vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => useAuthMock(),
}));

vi.mock('../lib/api', () => ({
  apiGetWithoutAuthLogout: (...args: unknown[]) => apiGetWithoutAuthLogoutMock(...args),
}));

import ProtectedRoute from '../components/ProtectedRoute';

describe('ProtectedRoute', () => {
  beforeEach(() => {
    useAuthMock.mockReset();
    apiGetWithoutAuthLogoutMock.mockReset();
  });

  it('renders loading state when authentication is loading', () => {
    useAuthMock.mockReturnValue({ user: null, loading: true });

    render(
      <MemoryRouter>
        <ProtectedRoute>
          <div>Secret content</div>
        </ProtectedRoute>
      </MemoryRouter>,
    );

    expect(screen.getByText('Checking authentication...')).toBeInTheDocument();
  });

  it('redirects unauthenticated users to login', async () => {
    useAuthMock.mockReturnValue({ user: null, loading: false });

    render(
      <MemoryRouter initialEntries={['/protected']}>
        <Routes>
          <Route path="/login" element={<div>Login page</div>} />
          <Route
            path="/protected"
            element={
              <ProtectedRoute>
                <div>Secret content</div>
              </ProtectedRoute>
            }
          />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByText('Login page')).toBeInTheDocument();
  });

  it('renders protected children when the user is authenticated', () => {
    useAuthMock.mockReturnValue({ user: { uid: 'user-1', email: 'user@example.com' }, loading: false });

    render(
      <MemoryRouter initialEntries={['/protected']}>
        <Routes>
          <Route
            path="/protected"
            element={
              <ProtectedRoute>
                <div>Secret content</div>
              </ProtectedRoute>
            }
          />
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByText('Secret content')).toBeInTheDocument();
  });

  it('allows admins through role-guarded routes', async () => {
    useAuthMock.mockReturnValue({ user: { uid: 'admin-1', email: 'admin@example.com' }, loading: false });
    apiGetWithoutAuthLogoutMock.mockResolvedValue({ id: 'admin-1', role: 'admin' });

    render(
      <MemoryRouter initialEntries={['/admin']}>
        <Routes>
          <Route
            path="/admin"
            element={
              <ProtectedRoute allowedRoles={['admin', 'moderator']}>
                <div>Admin console</div>
              </ProtectedRoute>
            }
          />
          <Route path="/unauthorized" element={<div>Unauthorized page</div>} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByText('Admin console')).toBeInTheDocument();
  });

  it('redirects non-admin users away from admin routes', async () => {
    useAuthMock.mockReturnValue({ user: { uid: 'user-1', email: 'user@example.com' }, loading: false });
    apiGetWithoutAuthLogoutMock.mockResolvedValue({ id: 'user-1', role: 'user' });

    render(
      <MemoryRouter initialEntries={['/admin']}>
        <Routes>
          <Route
            path="/admin"
            element={
              <ProtectedRoute allowedRoles={['admin', 'moderator']}>
                <div>Admin console</div>
              </ProtectedRoute>
            }
          />
          <Route path="/unauthorized" element={<div>Unauthorized page</div>} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByText('Unauthorized page')).toBeInTheDocument();
  });

  it('fails closed when backend role verification is unavailable', async () => {
    useAuthMock.mockReturnValue({ user: { uid: 'admin-1', email: 'admin@example.com' }, loading: false });
    apiGetWithoutAuthLogoutMock.mockRejectedValue(new Error('Backend unavailable'));

    render(
      <MemoryRouter initialEntries={['/admin']}>
        <Routes>
          <Route
            path="/admin"
            element={
              <ProtectedRoute allowedRoles={['admin']}>
                <div>Admin console</div>
              </ProtectedRoute>
            }
          />
          <Route path="/unauthorized" element={<div>Unauthorized page</div>} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByText('Unauthorized page')).toBeInTheDocument();
  });
});
