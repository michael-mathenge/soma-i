import { rmSync } from "node:fs";
import { dirname } from "node:path";
import { assertIsolatedDatabase } from "../test-support/e2e-database-guard.js";

export default async function globalTeardown() {
  const databaseUrl = process.env.SOMAI_E2E_DATABASE_URL;
  if (!databaseUrl) return;
  const databasePath = assertIsolatedDatabase(databaseUrl);
  const databaseDirectory = dirname(databasePath);
  try {
    rmSync(databaseDirectory, { recursive: true, force: true });
  } catch (error) {
    if (error.code !== "EPERM") throw error;
    console.warn(
      `Temporary Playwright database remains at ${databaseDirectory}`,
    );
  }
}
