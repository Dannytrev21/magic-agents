import type { HTMLAttributes } from "react";

import styles from "@/components/primitives/Text.module.css";

type TextProps = HTMLAttributes<HTMLParagraphElement> & {
  tone?: "default" | "muted" | "subtle";
};

export function Text({ tone = "default", className, ...props }: TextProps) {
  const toneClass =
    tone === "muted" ? styles.muted : tone === "subtle" ? styles.subtle : "";

  return (
    <p
      className={[styles.text, toneClass, className].filter(Boolean).join(" ")}
      {...props}
    />
  );
}
