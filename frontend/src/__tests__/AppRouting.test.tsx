import React from 'react';
import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({ user: null, loading: false, token: null, login: vi.fn(), register: vi.fn(), loginWithGoogle: vi.fn(), logout: vi.fn(), configError: null }),
}));

vi.mock('../ui/theme', () => ({
  useTheme: () => ({ theme: 'light' }),
}));

vi.mock('../layout/Sidebar', () => ({ default: () => <div>Sidebar</div> }));
vi.mock('../layout/Topbar', () => ({ default: () => <div>Topbar</div> }));
vi.mock('../layout/RightSidebar', () => ({ default: () => <div>RightSidebar</div> }));
vi.mock('../layout/BottomNav', () => ({ default: () => <div>BottomNav</div> }));
vi.mock('../components/ProtectedRoute', () => ({ default: ({ children }: { children: React.ReactNode }) => <>{children}</> }));
vi.mock('../pages/Dashboard', () => ({ default: () => <div>Dashboard page</div> }));
vi.mock('../pages/Feed', () => ({ default: () => <div>Feed page</div> }));
vi.mock('../pages/Chat', () => ({ default: () => <div>Chat page</div> }));
vi.mock('../pages/Groups', () => ({ default: () => <div>Groups page</div> }));
vi.mock('../pages/Search', () => ({ default: () => <div>Search page</div> }));
vi.mock('../features/auth/Login', () => ({ default: () => <div>Login page</div> }));
vi.mock('../pages/Profile', () => ({ default: () => <div>Profile page</div> }));
vi.mock('../features/auth/Register', () => ({ default: () => <div>Register page</div> }));
vi.mock('../features/auth/Onboarding', () => ({ default: () => <div>Onboarding page</div> }));
vi.mock('../pages/Unauthorized', () => ({ default: () => <div>Unauthorized page</div> }));
vi.mock('../pages/NotFound', () => ({ default: () => <div>NotFound page</div> }));

import App from '../App';

describe('App routing integration', () => {
  it('renders the login route when the user is unauthenticated', async () => {
    render(
      <MemoryRouter initialEntries={['/login']}>
        <App />
      </MemoryRouter>,
    );

    expect(await screen.findByText('Login page')).toBeInTheDocument();
  });
});
