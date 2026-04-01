import type { ButtonHTMLAttributes, ReactNode } from "react";

import styles from "@/components/primitives/Button.module.css";

type ButtonVariant = "primary" | "secondary" | "ghost";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  isLoading?: boolean;
  leadingIcon?: ReactNode;
};

export function Button({
  children,
  variant = "primary",
  isLoading = false,
  leadingIcon,
  disabled,
  className,
  ...props
}: ButtonProps) {
  const stateClass =
    variant === "secondary"
      ? styles.secondary
      : variant === "ghost"
        ? styles.ghost
        : styles.primary;

  return (
    <button
      type="button"
      className={[styles.button, stateClass, className].filter(Boolean).join(" ")}
      disabled={disabled || isLoading}
      aria-busy={isLoading ? "true" : undefined}
      {...props}
    >
      {isLoading ? <span className={styles.spinner} aria-hidden="true" /> : leadingIcon}
      <span>{children}</span>
    </button>
  );
}
