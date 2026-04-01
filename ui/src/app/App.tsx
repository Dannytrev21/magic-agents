import { RouterProvider, createBrowserRouter } from 'react-router-dom';
import { AppErrorBoundary } from '@/app/AppErrorBoundary';
import { AppProviders } from '@/app/AppProviders';
import { appRoutes } from '@/app/routes';

const appRouter = createBrowserRouter(appRoutes);

export function App() {
  return (
    <AppProviders>
      <AppErrorBoundary>
        <RouterProvider router={appRouter} />
      </AppErrorBoundary>
    </AppProviders>
  );
}
