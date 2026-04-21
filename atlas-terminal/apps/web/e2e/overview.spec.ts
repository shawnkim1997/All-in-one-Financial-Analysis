import { expect, test } from "@playwright/test";

import { expectAtlasShell, mockAtlasApi, seedTicker } from "./atlas-smoke";

test("overview loads with the ATLAS shell", async ({ page }) => {
  await mockAtlasApi(page);
  await seedTicker(page, "NVDA");

  await page.goto("/");

  await expectAtlasShell(page);
  await expect(page.getByRole("heading", { name: "NVDA Overview" })).toBeVisible();
});
