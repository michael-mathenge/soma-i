import { rmSync } from "node:fs";
import { basename, dirname } from "node:path";
import { setTimeout } from "node:timers/promises";
import { assertIsolatedDatabase } from "../test-support/e2e-database-guard.js";

export async function removeTemporaryDatabase(
  databaseUrl,
  { remove = rmSync, wait = setTimeout, warn = console.warn } = {},
) {
  if (!databaseUrl) return;
  for (let attempt = 0; attempt < 4; attempt += 1) {
    const databaseDirectory = dirname(assertIsolatedDatabase(databaseUrl));
    if (!/^somai-playwright-.+/.test(basename(databaseDirectory))) {
      throw new Error("Teardown may only delete a somai-playwright-* folder.");
    }
    try {
      remove(databaseDirectory, { recursive: true, force: true });
      return;
    } catch (error) {
      if (!["EBUSY", "EPERM", "ENOTEMPTY"].includes(error.code)) throw error;
      if (attempt === 3) {
        warn(`Temporary Playwright database remains at ${databaseDirectory}`);
        return;
      }
      await wait(100);
    }
  }
}

export default async function globalTeardown() {
  await removeTemporaryDatabase(process.env.SOMAI_E2E_DATABASE_URL);
}
