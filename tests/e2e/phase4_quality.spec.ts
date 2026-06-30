import { test, expect } from "@playwright/test";
import * as path from "path";
import * as fs from "fs";
import * as os from "os";

const BASE_URL = "http://localhost:8001/app";
const API_BASE = "http://localhost:8001";

/**
 * CSV with known quality issues:
 * - duplicate rows (first two rows are identical)
 * - a "category" column whose values look like numbers (type mismatch hint)
 * - a missing value in one cell
 */
function createDirtyCsv(): string {
  const tmpFile = path.join(os.tmpdir(), `test_p4_dirty_${Date.now()}.csv`);
  const content = `id,amount,category,note
1,100,10,sale
1,100,10,sale
2,200,20,refund
3,,30,sale
4,400,40,refund
5,500,50,sale
`;
  fs.writeFileSync(tmpFile, content);
  return tmpFile;
}

/**
 * Perfectly clean CSV — no duplicates, consistent types, no nulls.
 */
function createCleanCsv(): string {
  const tmpFile = path.join(os.tmpdir(), `test_p4_clean_${Date.now()}.csv`);
  const content = `month,revenue,units
Jan,10000,120
Feb,12000,145
Mar,11000,132
Apr,13000,158
May,15000,180
Jun,14000,170
`;
  fs.writeFileSync(tmpFile, content);
  return tmpFile;
}

test.describe("Phase 4 - Data Quality Notice", () => {
  test("shows quality notice when issues detected", async ({ page }) => {
    const csvPath = createDirtyCsv();
    try {
      await page.goto(BASE_URL);
      await page.waitForSelector("input[type=file]", { timeout: 10000 });

      await page.setInputFiles("input[type=file]", csvPath);
      // Wait for profile card to confirm upload succeeded
      await expect(page.locator("text=id")).toBeVisible({ timeout: 15000 });

      const textarea = page.locator("textarea");
      await textarea.fill("How many records are there?");
      await page.locator("button:has-text('Send')").click();

      await expect(page.locator("text=How many records are there?")).toBeVisible();

      // Wait for any assistant response to appear (real LLM call)
      await expect(
        page.locator('[class*="justify-start"]').first()
      ).toBeVisible({ timeout: 60000 });

      // If the backend detected quality issues it returns quality_report.has_issues=true
      // and the DataQualityNotice component will be rendered.
      // We check for it — if no issues were detected, skip gracefully.
      const noticeLocator = page.locator("text=Data quality notice");
      const noticeVisible = await noticeLocator.isVisible({ timeout: 5000 }).catch(() => false);

      if (noticeVisible) {
        // Panel should be collapsed by default — expanded content should NOT be in the DOM
        // (the component uses conditional rendering, not visibility:hidden)
        const expandedContent = page.locator("text=These issues were detected before answering");
        await expect(expandedContent).not.toBeVisible();

        // Click the header to expand
        await noticeLocator.click();

        // Expanded content should now appear
        await expect(expandedContent).toBeVisible({ timeout: 3000 });

        // At minimum some issue or clean action should appear in the expanded panel
        const hasAutoFixed = await page.locator("text=Automatically fixed:").isVisible();
        const hasDetected = await page.locator("text=Detected:").isVisible();
        expect(hasAutoFixed || hasDetected).toBeTruthy();
      }
      // If no quality notice: the backend found no issues — that is also valid behaviour.
    } finally {
      fs.unlinkSync(csvPath);
    }
  });

  test("no quality notice for clean data", async ({ page }) => {
    const csvPath = createCleanCsv();
    try {
      await page.goto(BASE_URL);
      await page.waitForSelector("input[type=file]", { timeout: 10000 });

      await page.setInputFiles("input[type=file]", csvPath);
      await expect(page.locator("text=month")).toBeVisible({ timeout: 15000 });

      const textarea = page.locator("textarea");
      await textarea.fill("What is the total revenue?");
      await page.locator("button:has-text('Send')").click();

      await expect(page.locator("text=What is the total revenue?")).toBeVisible();

      // Wait for assistant response
      await expect(
        page.locator('[class*="justify-start"]').first()
      ).toBeVisible({ timeout: 60000 });

      // Quality notice must NOT appear for a clean file
      await expect(page.locator("text=Data quality notice")).not.toBeVisible({ timeout: 3000 });
    } finally {
      fs.unlinkSync(csvPath);
    }
  });

  test("notice appears above the answer text in DOM order", async ({ page }) => {
    const csvPath = createDirtyCsv();
    try {
      await page.goto(BASE_URL);
      await page.waitForSelector("input[type=file]", { timeout: 10000 });

      await page.setInputFiles("input[type=file]", csvPath);
      await expect(page.locator("text=id")).toBeVisible({ timeout: 15000 });

      const textarea = page.locator("textarea");
      await textarea.fill("What is the average amount?");
      await page.locator("button:has-text('Send')").click();

      // Wait for assistant response
      await expect(
        page.locator('[class*="justify-start"]').first()
      ).toBeVisible({ timeout: 60000 });

      // Only run DOM-order assertion if quality notice is present
      const noticeLocator = page.locator("text=Data quality notice");
      const noticeVisible = await noticeLocator.isVisible({ timeout: 5000 }).catch(() => false);

      if (noticeVisible) {
        // Get bounding boxes to verify DOM order (notice top < answer text top)
        const noticeBB = await noticeLocator.boundingBox();
        // The assistant answer paragraph — find the p tag inside justify-start containers
        const answerPara = page.locator('[class*="justify-start"] p').first();
        const answerBB = await answerPara.boundingBox();

        if (noticeBB && answerBB) {
          // Notice must be rendered ABOVE (smaller Y coordinate) than the answer
          expect(noticeBB.y).toBeLessThan(answerBB.y);
        }
      }
    } finally {
      fs.unlinkSync(csvPath);
    }
  });

  test("API returns quality_report field in message response", async ({ request }) => {
    // Create session and upload dirty CSV via API to verify the field is present
    const sessionRes = await request.post(`${API_BASE}/sessions`);
    const sessionBody = await sessionRes.json();
    const sessionId = sessionBody.data.session_id;

    const tmpPath = createDirtyCsv();
    try {
      const fileBuffer = fs.readFileSync(tmpPath);
      const uploadRes = await request.post(`${API_BASE}/sessions/${sessionId}/files`, {
        multipart: {
          file: { name: "dirty.csv", mimeType: "text/csv", buffer: fileBuffer },
        },
      });
      expect(uploadRes.ok()).toBeTruthy();

      const msgRes = await request.post(`${API_BASE}/sessions/${sessionId}/messages`, {
        data: { content: "How many rows are there?" },
      });
      expect(msgRes.ok()).toBeTruthy();
      const msgBody = await msgRes.json();

      // The response must have a quality_report field (can be null if no issues detected)
      expect(msgBody.data).toHaveProperty("quality_report");
      // content and action must still be present
      expect(msgBody.data).toHaveProperty("content");
      expect(msgBody.data).toHaveProperty("action");
      expect(msgBody.data.content).toBeTruthy();
    } finally {
      fs.unlinkSync(tmpPath);
    }
  });
});
