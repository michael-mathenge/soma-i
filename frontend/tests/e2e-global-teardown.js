import { rmSync } from "node:fs";

export default async function globalTeardown() {
  const databaseDirectory = process.env.SOMAI_E2E_DB_DIR;
  if (databaseDirectory) {
    try {
      rmSync(databaseDirectory, { recursive: true, force: true });
    } catch (error) {
      if (error.code !== "EPERM") throw error;
      console.warn(`Temporary Playwright database remains at ${databaseDirectory}`);
    }
  }
}
