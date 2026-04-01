import { readFileSync, readdirSync, statSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

import base from "@/styles/base.css?raw";
import tokens from "@/styles/tokens.css?raw";

function walkStyleFiles(root: string): string[] {
  return readdirSync(root).flatMap((entry) => {
    const fullPath = `${root}/${entry}`;
    if (statSync(fullPath).isDirectory()) {
      return walkStyleFiles(fullPath);
    }

    return fullPath.endsWith(".css") ? [fullPath] : [];
  });
}

describe("design tokens", () => {
  it("defines the workspace token system and typography roles", () => {
    expect(tokens).toContain("--color-canvas");
    expect(tokens).toContain("--color-signal");
    expect(tokens).toContain("--font-sans");
    expect(tokens).toContain("--font-mono");
    expect(tokens).toContain("--motion-quick");
    expect(base).toContain("font-family: var(--font-sans)");
    expect(base).toContain("font-family: var(--font-mono)");
  });

  it("keeps shared component styles on tokens instead of hex values", () => {
    const stylesRoot = fileURLToPath(new URL("../components", import.meta.url));

    for (const filePath of walkStyleFiles(stylesRoot)) {
      const contents = readFileSync(filePath, "utf8");
      expect(contents, filePath).not.toMatch(/#[0-9a-fA-F]{3,8}\b/);
    }
  });
});
