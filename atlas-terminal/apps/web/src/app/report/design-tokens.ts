/**
 * Morgan Stanley Blue design tokens used by the institutional report.
 *
 * NOTE: P1-8 will hoist these into `tailwind.config.ts` so the rest of the app
 * shares the same palette. Until then, both this constant and the global
 * tailwind tokens (Terminal Noir) coexist intentionally.
 */
export const C = {
  navy: "#1B2A4A",
  blue: "#2E5B9A",
  gold: "#C4A35A",
  green: "#2D8B5E",
  red: "#C0392B",
  gray: "#6B7B8D",
  lightGray: "#E8ECF0",
  bg: "#FFFFFF",
  text: "#1A1A2E",
  muted: "#6B7B8D",
} as const;
