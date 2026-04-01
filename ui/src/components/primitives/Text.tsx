import clsx from 'clsx';
import type { ElementType, ReactNode } from 'react';
import styles from '@/components/primitives/primitives.module.css';

type TextSize = 'xs' | 'sm' | 'base' | 'lg' | 'xl';
type TextTone = 'default' | 'muted' | 'signal';
type TextWeight = 'regular' | 'medium' | 'semibold';

type TextProps = {
  as?: ElementType;
  children: ReactNode;
  className?: string;
  size?: TextSize;
  tone?: TextTone;
  weight?: TextWeight;
} & Record<string, unknown>;

function sizeClassName(size: TextSize) {
  switch (size) {
    case 'xs':
      return styles.textXs;
    case 'sm':
      return styles.textSm;
    case 'lg':
      return styles.textLg;
    case 'xl':
      return styles.textXl;
    default:
      return styles.textBase;
  }
}

function toneClassName(tone: TextTone) {
  switch (tone) {
    case 'muted':
      return styles.textMuted;
    case 'signal':
      return styles.textSignal;
    default:
      return undefined;
  }
}

function weightClassName(weight: TextWeight) {
  switch (weight) {
    case 'medium':
      return styles.weightMedium;
    case 'semibold':
      return styles.weightSemibold;
    default:
      return styles.weightRegular;
  }
}

export function Text({
  as: Component = 'p',
  children,
  className,
  size = 'base',
  tone = 'default',
  weight = 'regular',
  ...props
}: TextProps) {
  return (
    <Component
      {...(props as object)}
      className={clsx(
        styles.text,
        sizeClassName(size),
        toneClassName(tone),
        weightClassName(weight),
        className,
      )}
    >
      {children}
    </Component>
  );
}
