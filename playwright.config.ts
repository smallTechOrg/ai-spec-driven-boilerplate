import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  use: {
    baseURL: "http://localhost:8001/app",
    screenshot: "only-on-failure",
    headless: true,
  },
  timeout: 60000,
});
