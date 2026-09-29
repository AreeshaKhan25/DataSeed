/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        // Source Serif carries the headings; Mona Sans does the interface work.
        // The serif/geometric split is what keeps this from reading as a
        // generic dashboard template.
        serif: ['"Source Serif 4"', "Georgia", "serif"],
        sans: ['"Mona Sans"', "system-ui", "sans-serif"],
      },
      colors: {
        ink: { DEFAULT: "#16202e", soft: "#3c4757", mute: "#6b7684", faint: "#9aa3ae" },
        navy: { DEFAULT: "#1f4e79", deep: "#163a5c", light: "#2f6da3", wash: "#eef4fb" },
        canvas: { DEFAULT: "#f6f8fb", raised: "#ffffff", sunken: "#eef1f6" },
        line: { DEFAULT: "#e4e8ef", soft: "#eef1f6", strong: "#d3d9e3" },
        grass: { DEFAULT: "#1e8e3e", wash: "#e8f5ec" },
        amber: { DEFAULT: "#b06000", wash: "#fdf3e4" },
        rose: { DEFAULT: "#c5221f", wash: "#fdeceb" },
        iris: { DEFAULT: "#6d28d9", wash: "#f2ecfd" },
        teal: { DEFAULT: "#0e7490", wash: "#e6f4f8" },
      },
      borderRadius: { xl: "14px", "2xl": "18px", "3xl": "24px" },
      boxShadow: {
        card: "0 1px 2px rgba(22,32,46,.05), 0 1px 3px rgba(22,32,46,.04)",
        lift: "0 4px 12px rgba(22,32,46,.07), 0 12px 32px rgba(22,32,46,.06)",
        dock: "0 8px 28px rgba(15,23,35,.32), 0 2px 8px rgba(15,23,35,.22)",
      },
      transitionTimingFunction: { spring: "cubic-bezier(.16,1,.3,1)" },
    },
  },
  plugins: [],
};
