import { expect, type Page } from "@playwright/test";

export async function mockAtlasApi(page: Page) {
  await page.route("**/api/**", async (route) => {
    const url = new URL(route.request().url());
    const path = url.pathname;

    if (path.includes("/market/indices")) {
      await route.fulfill({
        json: [
          { label: "S&P 500", symbol: "^GSPC", price: "5,000.00", change: "+0.10%", positive: true },
          { label: "NASDAQ", symbol: "^IXIC", price: "16,000.00", change: "+0.20%", positive: true },
        ],
      });
      return;
    }

    if (path.includes("/market/overview/")) {
      await route.fulfill({ json: { asset_type: "equity", data: { name: "NVIDIA Corporation" } } });
      return;
    }

    if (path.includes("/market/sector/")) {
      await route.fulfill({ json: { sector: "Technology", industry: "Semiconductors" } });
      return;
    }

    if (path.includes("/market/health/")) {
      await route.fulfill({ json: { altman_z: 8.4, piotroski_score: 7 } });
      return;
    }

    if (path.includes("/portfolio/summary")) {
      await route.fulfill({ json: { positions: [], total_value: 0, total_pnl: 0, total_pnl_pct: 0 } });
      return;
    }

    if (path.includes("/fx/rates")) {
      await route.fulfill({ json: { rates: { USD_USD: 1, EUR_USD: 1.08, DKK_USD: 0.15 } } });
      return;
    }

    if (path.includes("/news/")) {
      await route.fulfill({ json: [] });
      return;
    }

    if (path.includes("/macro/fred/")) {
      await route.fulfill({ json: { data: [{ date: "2026-01-01", value: 4.0 }] } });
      return;
    }

    await route.fulfill({ json: {} });
  });
}

export async function seedTicker(page: Page, ticker = "NVDA") {
  await page.addInitScript((value) => {
    window.localStorage.setItem("atlas_active_ticker", value);
    window.localStorage.setItem(
      "atlas-terminal",
      JSON.stringify({
        state: {
          activeSymbol: value,
          activePage: "equity",
          recentSymbols: [value],
          currency: "USD",
          theme: "bloomberg",
          watchlist: [],
          layouts: {},
        },
        version: 1,
      }),
    );
  }, ticker);
}

export async function expectAtlasShell(page: Page) {
  await expect(page.getByText("ATLAS Desk")).toBeVisible();
  await expect(page.getByText("AI Copilot")).toBeVisible();
}
