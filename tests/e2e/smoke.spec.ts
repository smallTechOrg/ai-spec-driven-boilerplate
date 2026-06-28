import { test, expect } from '@playwright/test'
import path from 'path'
import fs from 'fs'

test.describe('Phase 1 smoke — CSV upload + question + chart', () => {
  test('renders the page with sidebar and chat panel', async ({ page }) => {
    await page.goto('http://localhost:8001/app/')
    await expect(page.locator('text=Data Analysis Agent')).toBeVisible()
    await expect(page.locator('text=Upload CSV')).toBeVisible()
  })

  test('uploads a CSV and shows schema preview', async ({ page }) => {
    // Create a temp CSV file
    const csvContent = 'region,revenue,units\nNorth,12500,42\nSouth,9800,31\nEast,15200,58\n'
    const csvPath = path.join('/tmp', 'test_upload.csv')
    fs.writeFileSync(csvPath, csvContent)

    await page.goto('http://localhost:8001/app/')

    // Upload file
    const fileInput = page.locator('input[type="file"]')
    await fileInput.setInputFiles(csvPath)

    // Schema preview should appear
    await expect(page.locator('text=test_upload.csv').first()).toBeVisible({ timeout: 10000 })
    await expect(page.locator('text=region')).toBeVisible()
  })

  test('asks a question and gets an answer with chart', async ({ page }) => {
    const csvContent =
      'region,revenue,units\nNorth,12500,42\nSouth,9800,31\nEast,15200,58\nWest,8700,29\n'
    const csvPath = path.join('/tmp', 'test_analysis.csv')
    fs.writeFileSync(csvPath, csvContent)

    await page.goto('http://localhost:8001/app/')

    // Upload file
    const fileInput = page.locator('input[type="file"]')
    await fileInput.setInputFiles(csvPath)
    await expect(page.locator('text=test_analysis.csv').first()).toBeVisible({ timeout: 10000 })

    // Select the file (click on it in sidebar)
    await page.locator('text=test_analysis.csv').first().click()

    // Type question
    const questionInput = page
      .locator('input[placeholder*="question"], textarea[placeholder*="question"]')
      .first()
    await questionInput.fill('What is the total revenue by region?')
    await questionInput.press('Enter')

    // Wait for answer (LLM takes time — 60s timeout)
    await expect(page.locator('[data-testid="answer-card"]').first()).toBeVisible({
      timeout: 60000,
    })

    // Wait for chart (only appears after full LLM response and chart renders)
    await expect(page.locator('.plotly, [class*="plotly"]').first()).toBeVisible({
      timeout: 90000,
    })
  })
})
