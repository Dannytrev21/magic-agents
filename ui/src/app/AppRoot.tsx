import { BrowserRouter, Route, Routes } from "react-router-dom";

import { AppErrorBoundary } from "@/app/AppErrorBoundary";
import { AppProviders } from "@/app/AppProviders";
import { NotFoundView } from "@/app/NotFoundView";
import { WorkspaceRoute } from "@/app/WorkspaceRoute";

export function AppRoot() {
  return (
    <AppProviders>
      <BrowserRouter>
        <AppErrorBoundary>
          <Routes>
            <Route path="/" element={<WorkspaceRoute />} />
            <Route path="*" element={<NotFoundView />} />
          </Routes>
        </AppErrorBoundary>
      </BrowserRouter>
    </AppProviders>
  );
}
