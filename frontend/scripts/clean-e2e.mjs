import { readdirSync, rmSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { tmpdir } from "node:os";
import { assertIsolatedDatabase } from "../test-support/e2e-database-guard.js";

const temporaryDirectory = resolve(tmpdir());
for (const entry of readdirSync(temporaryDirectory, { withFileTypes: true })) {
  if (!entry.isDirectory() || !entry.name.startsWith("somai-playwright-")) {
    continue;
  }

  const databasePath = join(temporaryDirectory, entry.name, "test.sqlite3");
  const validatedDatabasePath = assertIsolatedDatabase(
    `sqlite:///${encodeURI(databasePath.replaceAll("\\", "/"))}`,
  );
  const directoryPath = dirname(validatedDatabasePath);
  rmSync(directoryPath, { recursive: true, force: true });
  console.log(`Removed Playwright temp folder ${directoryPath}`);
}
