import { expect, test } from "@playwright/test";

import { expectAtlasShell, mockAtlasApi, seedTicker } from "./atlas-smoke";

test("portfolio loads without live provider calls", async ({ page }) => {
  await mockAtlasApi(page);
  await seedTicker(page, "NVDA");

  await page.goto("/portfolio");

  await expectAtlasShell(page);
  await expect(page.getByRole("heading", { name: "Portfolio" })).toBeVisible();
});
