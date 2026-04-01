import type { HTMLAttributes } from "react";

import styles from "@/components/primitives/MonoText.module.css";

type MonoTextProps = HTMLAttributes<HTMLElement> & {
  as?: "code" | "span";
};

export function MonoText({ as = "code", children, className, ...props }: MonoTextProps) {
  const Component = as;

  return (
    <Component className={[styles.mono, className].filter(Boolean).join(" ")} {...props}>
      {children}
    </Component>
  );
}
