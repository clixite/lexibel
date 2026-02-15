import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: "#1B365D",
          50: "#E8EDF3",
          100: "#D1DBE7",
          200: "#A3B7CF",
          300: "#7593B7",
          400: "#476F9F",
          500: "#1B365D",
          600: "#162C4D",
          700: "#11213A",
          800: "#0B1627",
          900: "#060B13",
        },
        secondary: {
          DEFAULT: "#3A7CA5",
          50: "#EBF3F8",
          100: "#D7E7F1",
          200: "#AFCFE3",
          300: "#87B7D5",
          400: "#5F9FC7",
          500: "#3A7CA5",
          600: "#2E6384",
          700: "#234A63",
          800: "#173142",
          900: "#0C1921",
        },
        accent: {
          DEFAULT: "#F39C12",
          50: "#FEF5E7",
          500: "#F39C12",
          700: "#B8750E",
        },
        success: {
          DEFAULT: "#27AE60",
          50: "#E9F7EF",
          500: "#27AE60",
          700: "#1E8449",
        },
        danger: {
          DEFAULT: "#E74C3C",
          50: "#FDEDEB",
          500: "#E74C3C",
          700: "#C0392B",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;
