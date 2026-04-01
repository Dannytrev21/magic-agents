import type { HTMLAttributes } from "react";

import styles from "@/components/primitives/Badge.module.css";

type BadgeProps = HTMLAttributes<HTMLSpanElement> & {
  tone?: "signal" | "muted";
};

export function Badge({ children, tone = "signal", className, ...props }: BadgeProps) {
  return (
    <span
      className={[
        styles.badge,
        tone === "muted" ? styles.muted : "",
        className,
      ]
        .filter(Boolean)
        .join(" ")}
      {...props}
    >
      {children}
    </span>
  );
}
