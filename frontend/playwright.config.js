import { defineConfig } from "@playwright/test";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { assertIsolatedDatabase } from "./test-support/e2e-database-guard.js";

const inheritedDatabaseDirectory = process.env.SOMAI_E2E_DB_DIR;
const candidateDatabaseDirectory = inheritedDatabaseDirectory
  ? inheritedDatabaseDirectory
  : mkdtempSync(join(tmpdir(), "somai-playwright-"));
const candidateDatabasePath = join(candidateDatabaseDirectory, "test.sqlite3");
const candidateDatabaseUrl = `sqlite:///${candidateDatabasePath.replaceAll("\\", "/")}`;
const databasePath = assertIsolatedDatabase(candidateDatabaseUrl);
const databaseDirectory = dirname(databasePath);
const databaseUrl = `sqlite:///${databasePath.replaceAll("\\", "/")}`;
const apiPort = "8127";
const uiPort = "4177";
const e2eEnv = {
  ...process.env,
  DATABASE_URL: databaseUrl,
  SOMAI_E2E_DATABASE_URL: databaseUrl,
  SOMAI_E2E_DB_DIR: databaseDirectory,
  SOMAI_E2E_API_PORT: apiPort,
  SOMAI_E2E_UI_PORT: uiPort,
};

Object.assign(process.env, {
  DATABASE_URL: databaseUrl,
  SOMAI_E2E_DATABASE_URL: databaseUrl,
  SOMAI_E2E_DB_DIR: databaseDirectory,
  SOMAI_E2E_API_PORT: apiPort,
  SOMAI_E2E_UI_PORT: uiPort,
});

export default defineConfig({
  testDir: "./tests",
  workers: 1,
  globalSetup: "./tests/e2e-global-setup.js",
  globalTeardown: "./tests/e2e-global-teardown.js",
  use: {
    baseURL: `http://127.0.0.1:${uiPort}`,
    browserName: "chromium",
    ...(process.env.PLAYWRIGHT_CHANNEL
      ? { channel: process.env.PLAYWRIGHT_CHANNEL }
      : {}),
  },
  webServer: [
    {
      command: "node ../backend/serve-dev.mjs",
      url: `http://127.0.0.1:${apiPort}/api/health/`,
      reuseExistingServer: false,
      env: e2eEnv,
      timeout: 120000,
    },
    {
      command: "node serve-e2e.mjs",
      url: `http://127.0.0.1:${uiPort}`,
      reuseExistingServer: false,
      env: e2eEnv,
      timeout: 120000,
    },
  ],
});
