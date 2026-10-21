import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { proxy: { "/api": "http://127.0.0.1:8000" } },
  // Keep authored custom-property values intact across Vite 8's CSS minifier change.
  build: { target: "es2020", cssMinify: false },
});
