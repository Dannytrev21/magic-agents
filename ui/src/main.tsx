import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { AppRoot } from "@/app/AppRoot";
import "@/styles/base.css";

const rootElement = document.getElementById("root");

if (!rootElement) {
  throw new Error("Root element not found");
}

createRoot(rootElement).render(
  <StrictMode>
    <AppRoot />
  </StrictMode>,
);
