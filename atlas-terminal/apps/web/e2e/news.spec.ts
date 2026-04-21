import { expect, test } from "@playwright/test";

import { expectAtlasShell, mockAtlasApi, seedTicker } from "./atlas-smoke";

test("news route loads with mocked articles", async ({ page }) => {
  await mockAtlasApi(page);
  await seedTicker(page, "NVDA");

  await page.goto("/news");

  await expectAtlasShell(page);
  await expect(page.getByRole("heading", { name: "NVDA News Feed" })).toBeVisible();
});
