import type { RouteObject } from 'react-router-dom';
import { NotFoundPage } from '@/app/NotFoundPage';
import { OperatorWorkspacePage } from '@/features/workspace/OperatorWorkspacePage';

export const appRoutes: RouteObject[] = [
  {
    path: '/',
    element: <OperatorWorkspacePage />,
  },
  {
    path: '*',
    element: <NotFoundPage />,
  },
];
