import fontsCss from '@/styles/fonts.css?raw';
import globalCss from '@/styles/global.css?raw';
import tokensCss from '@/styles/tokens.css?raw';
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

  it('adds the graphite and bone visual-system tokens for the operator workspace', () => {
    expect(tokensCss).toContain('--color-bone');
    expect(tokensCss).toContain('--color-graphite');
    expect(tokensCss).toContain('--color-surface-raised');
    expect(tokensCss).toContain('--shadow-panel');
  });

  it('ships reduced-motion and screen-reader utility rules', () => {
    expect(globalCss).toContain('.srOnly');
    expect(globalCss).toContain('prefers-reduced-motion: reduce');
    expect(globalCss).toContain('scroll-behavior');
  });
});
