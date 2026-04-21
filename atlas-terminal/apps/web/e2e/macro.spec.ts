import { expect, test } from "@playwright/test";

import { expectAtlasShell, mockAtlasApi, seedTicker } from "./atlas-smoke";

test("macro dashboard route loads", async ({ page }) => {
  await mockAtlasApi(page);
  await seedTicker(page, "NVDA");

  await page.goto("/macro");

  await expectAtlasShell(page);
  await expect(page.getByRole("heading", { name: "Global Macro & Smart Money" })).toBeVisible();
});
