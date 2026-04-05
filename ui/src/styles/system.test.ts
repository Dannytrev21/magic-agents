import fontsCss from '@/styles/fonts.css?raw';
import globalCss from '@/styles/global.css?raw';
import tokensCss from '@/styles/tokens.css?raw';
import { workspaceDesignSystem } from '@/styles/system';
import { describe, expect, it } from 'vitest';

describe('Design system styles', () => {
  it('defines the core workspace tokens', () => {
    expect(tokensCss).toContain('--color-bg');
    expect(tokensCss).toContain('--color-signal');
    expect(tokensCss).toContain('--space-4');
    expect(tokensCss).toContain('--text-base');
    expect(tokensCss).toContain('--motion-normal');
  });

  it('declares non-blocking font loading for sans and mono families', () => {
    expect(fontsCss).toContain('font-display: swap');
    expect(fontsCss).toContain('--font-sans');
    expect(fontsCss).toContain('--font-mono');
  });

  it('mirrors typed visual tokens into CSS variables and provides reduced-motion fallbacks', () => {
    expect(workspaceDesignSystem.visualThesis).toMatch(/calm/i);
    expect(tokensCss).toContain(`--color-bg: ${workspaceDesignSystem.color.bg};`);
    expect(tokensCss).toContain(`--color-signal: ${workspaceDesignSystem.color.signal};`);
    expect(tokensCss).toContain(`--space-6: ${workspaceDesignSystem.space['6']};`);
    expect(tokensCss).toContain(`--radius-xl: ${workspaceDesignSystem.radius.xl};`);
    expect(tokensCss).toContain(`--motion-panel: ${workspaceDesignSystem.motion.panel};`);
    expect(tokensCss).toContain(`--surface-blur-medium: ${workspaceDesignSystem.material.blurMedium};`);
    expect(tokensCss).toContain('--shadow-floating:');
    expect(globalCss).toContain('@media (prefers-reduced-motion: reduce)');
  });
});
