import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Build straight into web/, which FastAPI serves at /. One command, one origin,
// no CORS in production and no separate static host to remember on demo day.
export default defineConfig({
  plugins: [react()],
  build: { outDir: "../web", emptyOutDir: true },
  server: {
    port: 5173,
    proxy: { "/api": "http://127.0.0.1:8000" },
  },
});
