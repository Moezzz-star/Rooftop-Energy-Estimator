import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { AuthContext, type AuthContextValue } from '@/hooks';
import { ProtectedRoute } from './ProtectedRoute';

function makeAuth(overrides: Partial<AuthContextValue>): AuthContextValue {
  return {
    user: null,
    isAuthenticated: false,
    isBootstrapping: false,
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
    ...overrides,
  };
}

function renderAt(auth: AuthContextValue): void {
  render(
    <AuthContext.Provider value={auth}>
      <MemoryRouter initialEntries={['/dashboard']}>
        <Routes>
          <Route path="/login" element={<div>Login page</div>} />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <div>Protected content</div>
              </ProtectedRoute>
            }
          />
        </Routes>
      </MemoryRouter>
    </AuthContext.Provider>,
  );
}

describe('ProtectedRoute', () => {
  it('redirects unauthenticated users to /login', () => {
    renderAt(makeAuth({ isAuthenticated: false }));
    expect(screen.getByText('Login page')).toBeInTheDocument();
    expect(screen.queryByText('Protected content')).not.toBeInTheDocument();
  });

  it('renders children when authenticated', () => {
    renderAt(
      makeAuth({
        isAuthenticated: true,
        user: {
          id: '3f2504e0-4f89-41d3-9a0c-0305e82c3301',
          email: 'user@example.com',
          is_active: true,
          date_joined: '2026-01-15T10:00:00Z',
        },
      }),
    );
    expect(screen.getByText('Protected content')).toBeInTheDocument();
  });

  it('shows a loader while bootstrapping', () => {
    renderAt(makeAuth({ isBootstrapping: true }));
    expect(screen.getByRole('status')).toBeInTheDocument();
  });
});
