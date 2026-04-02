import { render, screen } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { AppProviders } from '@/app/AppProviders';
import { AppErrorBoundary } from '@/app/AppErrorBoundary';
import { appRoutes } from '@/app/routes';

function renderRoute(initialEntries: string[]) {
  const router = createMemoryRouter(appRoutes, { initialEntries });
  return render(
    <AppProviders>
      <AppErrorBoundary>
        <RouterProvider router={router} />
      </AppErrorBoundary>
    </AppProviders>,
  );
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe('App shell', () => {
  it('renders the three-pane operator workspace landmarks', () => {
    renderRoute(['/']);

    expect(screen.getByRole('banner')).toBeInTheDocument();
    expect(screen.getByRole('complementary', { name: /story intake/i })).toBeInTheDocument();
    expect(screen.getByRole('main')).toBeInTheDocument();
    expect(screen.getByRole('complementary', { name: /evidence inspector/i })).toBeInTheDocument();
  });

  it('renders a controlled not found surface for unknown routes', async () => {
    renderRoute(['/missing']);

    expect(await screen.findByRole('heading', { name: /workspace not found/i })).toBeInTheDocument();
    expect(screen.getByText(/return to the active operator workspace/i)).toBeInTheDocument();
  });

  it('catches top-level rendering failures without crashing the tree', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => undefined);

    const Thrower = () => {
      throw new Error('boom');
    };

    render(
      <AppProviders>
        <AppErrorBoundary>
          <Thrower />
        </AppErrorBoundary>
      </AppProviders>,
    );

    expect(await screen.findByRole('heading', { name: /workspace unavailable/i })).toBeInTheDocument();
  });
});
