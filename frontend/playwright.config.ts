import { defineConfig, devices } from '@playwright/test'

// E2E smoke runs against the LIVE single-origin app served by the FastAPI backend at
// http://localhost:8001/app/ (the static export is mounted under /app). The backend must be
// running with a real Gemini key in .env before this suite runs — agent-builder's gate starts
// it. Override the base URL with E2E_BASE_URL if serving elsewhere.
const BASE_URL = process.env.E2E_BASE_URL ?? 'http://localhost:8001'

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 90_000,
  expect: { timeout: 60_000 },
  fullyParallel: false,
  retries: 0,
  reporter: 'line',
  use: {
    baseURL: BASE_URL,
    trace: 'on-first-retry',
    actionTimeout: 15_000,
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
})
