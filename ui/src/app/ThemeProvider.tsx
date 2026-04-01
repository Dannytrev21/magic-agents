import type { PropsWithChildren } from "react";
import { createContext, useContext, useEffect } from "react";

const ThemeContext = createContext("operator");

export function ThemeProvider({ children }: PropsWithChildren) {
  useEffect(() => {
    document.documentElement.dataset.theme = "operator";
  }, []);

  return <ThemeContext.Provider value="operator">{children}</ThemeContext.Provider>;
}

export function useTheme() {
  return useContext(ThemeContext);
}
