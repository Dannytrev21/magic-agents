import fontsCss from '@/styles/fonts.css?raw';
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
});
