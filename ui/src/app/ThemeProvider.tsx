import type { PropsWithChildren } from "react";
import { useEffect } from "react";

export function ThemeProvider({ children }: PropsWithChildren) {
  useEffect(() => {
    document.documentElement.dataset.theme = "operator";
  }, []);

  return children;
}
