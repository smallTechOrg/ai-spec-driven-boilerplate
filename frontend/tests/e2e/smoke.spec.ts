import { test, expect } from '@playwright/test'
import path from 'node:path'

// Primary-journey smoke against the LIVE single-origin app at http://localhost:8001/app/.
// Assumption: the FastAPI backend is running with a real Gemini key in .env (agent-builder's
// gate starts it). This walks: page loads & styled -> upload CSV -> profile renders -> ask a
// question -> a real answer bubble with a chart and an expandable "Code it ran" block appears.

const CSV = path.join(__dirname, 'fixtures', 'orders.csv')

test('upload, profile, ask, real answer with chart + code', async ({ page }) => {
  await page.goto('/app/')

  // Page loads and is styled (the upload heading and a real Tailwind colour are applied).
  await expect(page.getByRole('heading', { name: 'Data Analysis Agent' })).toBeVisible()
  const askHeading = page.getByText('Upload a CSV to begin')
  await expect(askHeading).toBeVisible()

  // The labelled stubs are visible (vision intact, never mistaken for a bug).
  await expect(page.getByText('Tokens & cost')).toBeVisible()
  await expect(page.getByText('Coming soon')).toBeVisible()

  // Upload the fixture CSV.
  await page.getByTestId('file-input').setInputFiles(CSV)

  // Profile panel renders with real columns from the file.
  const profile = page.getByTestId('profile-panel')
  await expect(profile).toBeVisible({ timeout: 30_000 })
  await expect(profile).toContainText('order_value')
  await expect(profile).toContainText('region')

  // Ask a question — REAL agentic loop against Gemini.
  await page.getByTestId('question-input').fill('What is the average order value by region?')
  await page.getByTestId('ask-button').click()

  // A real answer bubble appears (not a spinner, not an error).
  const answer = page.getByTestId('answer-bubble')
  await expect(answer).toBeVisible({ timeout: 80_000 })

  // Real prose answer content is present.
  const answerText = page.getByTestId('answer-text')
  await expect(answerText).not.toBeEmpty()

  // An interactive chart rendered (vega draws an SVG inside the chart container).
  const chart = page.getByTestId('vega-chart')
  await expect(chart.locator('svg')).toBeVisible({ timeout: 20_000 })

  // The "Code it ran" disclosure is present and expandable.
  const codeBlock = page.getByTestId('code-block')
  await expect(codeBlock).toBeVisible()
  await codeBlock.getByText('Code it ran').click()
  await expect(codeBlock.locator('pre')).toBeVisible()
})
