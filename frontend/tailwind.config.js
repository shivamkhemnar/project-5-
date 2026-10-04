/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        terminal: "#0B0E14",
        panel: "#11151F",
        border: "#1E2532",
        neon: "#10B981",
        crimson: "#EF4444",
        amber: "#F59E0B",
      },
    },
  },
  plugins: [],
};
