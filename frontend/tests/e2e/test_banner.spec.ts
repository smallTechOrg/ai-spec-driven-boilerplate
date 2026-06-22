import { test, expect } from '@playwright/test';

test('P1-AC1: stub banner visible on first paint', async ({ page }) => {
  await page.goto('http://localhost:3000');
  await expect(page.getByText('STUB MODE — responses are canned, not real AI output')).toBeVisible();
});
