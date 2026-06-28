import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 90000,
  use: {
    baseURL: 'http://localhost:8001',
    headless: true,
  },
  reporter: 'line',
})
