import { test, expect } from '@playwright/test';

test('P1-AC11: active session has bg-blue-100 and + New button visible', async ({ page }) => {
  await page.goto('http://localhost:3000');
  // Wait for sidebar to load
  await page.waitForTimeout(2000);
  // + New button always visible
  await expect(page.getByText('+ New')).toBeVisible();
  // At least one session item with bg-blue-100
  const activeSession = page.locator('.bg-blue-100');
  await expect(activeSession).toHaveCount(1);
});
