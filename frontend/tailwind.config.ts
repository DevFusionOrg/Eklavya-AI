import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: "var(--brand)",
        ink: "var(--ink)",
        surface: "var(--surface)",
        border: "var(--border)",
      },
    },
  },
  plugins: [],
};

export default config;
