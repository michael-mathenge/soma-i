import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  use: {
    baseURL: "http://127.0.0.1:4173",
    browserName: "chromium",
    ...(process.env.PLAYWRIGHT_CHANNEL
      ? { channel: process.env.PLAYWRIGHT_CHANNEL }
      : {}),
  },
  webServer: [
    {
      command: "node ../backend/serve-dev.mjs",
      url: "http://127.0.0.1:8000/api/health/",
      reuseExistingServer:
        process.env.PW_REUSE_SERVER === "true" || !process.env.CI,
      timeout: 120000,
    },
    {
      command: "node serve-e2e.mjs",
      url: "http://127.0.0.1:4173",
      reuseExistingServer:
        process.env.PW_REUSE_SERVER === "true" || !process.env.CI,
      timeout: 120000,
    },
  ],
});
