import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        surface: {
          canvas: "#FAFAFA",
          raised: "#FFFFFF",
          sunken: "#F1F3F6",
          overlay: "#FFFFFF",
        },
        brand: {
          navy: "#1B2A4A",
          blue: "#2E5B9A",
          "blue-hover": "#254A80",
          gold: "#C4A35A",
          "gold-soft": "#E4D2A6",
        },
        fin: {
          positive: "#2D8B5E",
          negative: "#C0392B",
          neutral: "#6B7B8D",
          warning: "#D9822B",
        },
        bg: {
          primary: "#FAFAFA",
          secondary: "#F1F3F6",
          card: "#FFFFFF",
          hover: "#F1F3F6",
        },
        accent: {
          green: "#1B2A4A",
          red: "#C0392B",
          yellow: "#C4A35A",
          blue: "#2E5B9A",
        },
        text: {
          primary: "#1A1A2E",
          secondary: "#4A5568",
          muted: "#6B7B8D",
        },
        border: {
          DEFAULT: "#E8ECF0",
          strong: "#CBD5DF",
          subtle: "#F1F3F6",
        },
      },
      fontFamily: {
        serif: ["var(--font-serif)", "Georgia", "serif"],
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "monospace"],
      },
      boxShadow: {
        card: "0 1px 0 #E8ECF0",
      },
    },
  },
  plugins: [],
};
export default config;
