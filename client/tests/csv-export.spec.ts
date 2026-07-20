import { test, expect } from "@playwright/test";

test("CSV export button exports inventory data", async ({ page, context }) => {
  // Navigate to inventory page
  await page.goto("http://localhost:3000");

  // Click Inventory nav link (by testing role)
  const inventoryLink = page.getByRole("link").filter({ hasText: "Inventory" });
  await inventoryLink.click();

  // Wait for table to load
  await page.waitForSelector("table tbody tr", { timeout: 5000 });
  console.log("✓ Inventory table loaded");

  // Get initial row count
  const rows = page.locator("table tbody tr");
  const rowCount = await rows.count();
  console.log(`✓ Found ${rowCount} inventory items`);

  // Set up download handler
  const downloadPromise = context.waitForEvent("download");

  // Click export button
  await page.click("button.export-button");

  // Get the download
  const download = await downloadPromise;
  const filename = download.suggestedFilename;
  console.log(`✓ File downloaded: ${filename}`);

  // Verify filename format includes timestamp
  expect(filename).toMatch(
    /^inventory-\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}\.csv$/,
  );

  // Save and read the file
  const path = await download.path();
  const fs = require("fs");
  const content = fs.readFileSync(path, "utf-8");
  const lines = content.split("\n").filter((l: string) => l.trim());

  console.log(`✓ CSV has ${lines.length} lines`);

  // Check header
  const header = lines[0];
  expect(header).toContain("SKU");
  expect(header).toContain("Item Name");
  expect(header).toContain("Quantity on Hand");
  console.log("✓ Header contains required columns");

  // Check data rows
  if (lines.length > 1) {
    const firstRow = lines[1];
    const columns = firstRow.split(",").length;
    expect(columns).toBe(9);
    console.log("✓ Data rows have correct column count");
  }
});
