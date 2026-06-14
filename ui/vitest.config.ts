import { defineConfig } from "vitest/config";

// Tests target the pure utility layer (src/lib) — no DOM needed, so the
// lightweight "node" environment keeps the run fast. Coverage is scoped to the
// tested helpers; components/hooks are validated via the build (tsc) instead.
export default defineConfig({
  test: {
    environment: "node",
    include: ["src/**/*.test.ts"],
    coverage: {
      provider: "v8",
      include: ["src/lib/format.ts", "src/lib/graph.ts"],
      reporter: ["text", "text-summary"],
      thresholds: { lines: 96, functions: 96, branches: 96, statements: 96 },
    },
  },
});
