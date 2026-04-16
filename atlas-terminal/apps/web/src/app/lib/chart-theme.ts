export const chartPalette = {
  navy: "#1B2A4A",
  blue: "#2E5B9A",
  gold: "#C4A35A",
  green: "#2D8B5E",
  red: "#C0392B",
  neutral: "#6B7B8D",
  neutralLight: "#CBD5DF",
  grid: "#E8ECF0",
  canvas: "#FFFFFF",
  sunken: "#F1F3F6",
  text: "#1A1A2E",
  textMuted: "#6B7B8D",
} as const;

export const categoricalChartColors = [
  chartPalette.navy,
  chartPalette.blue,
  chartPalette.gold,
  chartPalette.green,
  chartPalette.red,
  chartPalette.neutral,
] as const;

export const rechartsTheme = {
  gridStroke: chartPalette.grid,
  axisStroke: chartPalette.neutralLight,
  tickFill: chartPalette.textMuted,
  tooltip: {
    backgroundColor: chartPalette.canvas,
    border: `1px solid ${chartPalette.grid}`,
    color: chartPalette.text,
  },
} as const;

export const lightweightTheme = {
  layout: {
    background: { color: chartPalette.canvas },
    textColor: chartPalette.textMuted,
  },
  grid: {
    vertLines: { color: chartPalette.grid },
    horzLines: { color: chartPalette.grid },
  },
  timeScale: {
    borderColor: chartPalette.neutralLight,
  },
  rightPriceScale: {
    borderColor: chartPalette.neutralLight,
  },
} as const;
