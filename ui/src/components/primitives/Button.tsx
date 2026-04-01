import {
  Children,
  cloneElement,
  forwardRef,
  isValidElement,
  type AnchorHTMLAttributes,
  type ButtonHTMLAttributes,
  type ReactElement,
  type ReactNode,
} from 'react';
import clsx from 'clsx';
import styles from '@/components/primitives/primitives.module.css';

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger';

type SharedButtonProps = {
  asChild?: boolean;
  children: ReactNode;
  className?: string;
  loading?: boolean;
  variant?: ButtonVariant;
};

type NativeButtonProps = SharedButtonProps & ButtonHTMLAttributes<HTMLButtonElement>;
type AnchorButtonProps = SharedButtonProps & AnchorHTMLAttributes<HTMLAnchorElement>;

function variantClassName(variant: ButtonVariant) {
  switch (variant) {
    case 'secondary':
      return styles.buttonSecondary;
    case 'ghost':
      return styles.buttonGhost;
    case 'danger':
      return styles.buttonDanger;
    default:
      return styles.buttonPrimary;
  }
}

export const Button = forwardRef<HTMLButtonElement, NativeButtonProps | AnchorButtonProps>(
  function Button(
    { asChild = false, children, className, loading = false, variant = 'primary', ...props },
    ref,
  ) {
    const classes = clsx(styles.button, variantClassName(variant), className);
    const content = (
      <>
        {loading ? <span aria-hidden="true" className={styles.spinner} /> : null}
        <span>{children}</span>
      </>
    );

    if (asChild) {
      const child = Children.only(children);

      if (!isValidElement(child)) {
        throw new Error('Button with asChild expects a single valid element child.');
      }

      return cloneElement(child as ReactElement<{ className?: string }>, {
        className: clsx(classes, (child.props as { className?: string }).className),
      });
    }

    const nativeButtonProps = props as NativeButtonProps;
    const isDisabled = nativeButtonProps.disabled || loading;

    return (
      <button
        {...nativeButtonProps}
        className={classes}
        disabled={isDisabled}
        ref={ref}
        type={nativeButtonProps.type ?? 'button'}
      >
        {content}
      </button>
    );
  },
);
