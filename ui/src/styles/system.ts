export const workspaceDesignSystem = {
  visualThesis:
    'Calm graphite work surfaces, bone-forward typography, and restrained glass chrome with one warm signal accent.',
  surfaceMap: {
    content: 'Solid graphite workplanes for dense operator tasks.',
    chrome: 'Translucent bars, segmented controls, and inspector trim.',
    overlays: 'Lifted inspector and mobile navigation layers with softened blur.',
  },
  motionThesis: [
    'Pane and workspace changes settle with shallow fades and short vertical offsets.',
    'Interactive chrome brightens and lifts slightly instead of bouncing.',
    'Pipeline completion relies on focus handoff and live announcements over ornamental motion.',
  ],
  color: {
    bg: '#0f1115',
    bgElevated: '#161b20',
    surface: '#1b2129',
    surfaceStrong: '#242d38',
    border: '#46515f',
    borderStrong: '#5f6d7d',
    text: '#f4efe8',
    textMuted: '#c7beb2',
    ink: '#161311',
    signal: '#ffb347',
    success: '#63d1a7',
    warning: '#f6c76a',
    error: '#f08d74',
    info: '#89c2ff',
  },
  space: {
    '1': '0.25rem',
    '2': '0.5rem',
    '3': '0.75rem',
    '4': '1rem',
    '5': '1.5rem',
    '6': '2rem',
    '8': '3rem',
    '10': '4rem',
    '12': '5rem',
    '16': '6rem',
  },
  type: {
    xs: '0.75rem',
    sm: '0.875rem',
    base: '1rem',
    lg: '1.25rem',
    xl: '1.75rem',
  },
  leading: {
    tight: '1.2',
    normal: '1.5',
    relaxed: '1.65',
  },
  radius: {
    sm: '0.625rem',
    md: '0.875rem',
    lg: '1.125rem',
    xl: '1.5rem',
    round: '999px',
  },
  motion: {
    fast: '160ms',
    normal: '220ms',
    slow: '320ms',
    panel: '320ms',
  },
  material: {
    blurMedium: '20px',
    blurStrong: '30px',
  },
  shadow: {
    floating: '0 20px 48px rgba(7, 11, 18, 0.38)',
    soft: '0 12px 32px rgba(7, 11, 18, 0.24)',
  },
} as const;

export type WorkspaceDesignSystem = typeof workspaceDesignSystem;
