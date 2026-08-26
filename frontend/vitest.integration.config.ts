import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "node",
    globals: true,
    include: ["integration-tests/**/*.test.ts"],
    hookTimeout: 30000,
    testTimeout: 30000,
  },
});
