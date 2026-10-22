import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The API origin is configurable so the development server can point at a
// backend on a port other than 8000, which is often already taken.
const apiOrigin = process.env.SOMAI_API_ORIGIN || "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: { "/api": apiOrigin },
    port: Number(process.env.SOMAI_FRONTEND_PORT || 5173),
  },
  // Keep authored custom-property values intact across Vite 8's CSS minifier change.
  build: { target: "es2020", cssMinify: false },
});
