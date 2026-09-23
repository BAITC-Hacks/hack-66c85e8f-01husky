import { defineConfig } from "vitest/config";
import path from "node:path";

export default defineConfig({
  resolve: { alias: { "@": path.resolve(__dirname, "src"), "@mocks": path.resolve(__dirname, "mocks") } },
  test: { include: ["src/**/*.test.ts", "mocks/**/*.test.ts"] },
});
