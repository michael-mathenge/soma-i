import { readdirSync, rmSync, statSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { tmpdir } from "node:os";
import { assertIsolatedDatabase } from "../test-support/e2e-database-guard.js";

const temporaryPrefix = "somai-playwright-";
const recentWindowMs = 10 * 60 * 1000;

export function selectCleanupEntries(
  entries,
  { now = Date.now, recentWindow = recentWindowMs } = {},
) {
  const cutoff = now() - recentWindow;
  return entries
    .filter((entry) => entry.name.startsWith(temporaryPrefix))
    .map((entry) => {
      let reason = null;
      if (entry.hasJournalOrWal) {
        reason = "contains a SQLite -journal or -wal file";
      } else if (entry.modifiedAtMs >= cutoff) {
        reason = "modified in the last 10 minutes";
      }
      return { ...entry, skipReason: reason };
    });
}

function folderContainsJournalOrWal(directory) {
  for (const entry of readdirSync(directory, { withFileTypes: true })) {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) {
      if (folderContainsJournalOrWal(path)) return true;
    } else if (entry.name.endsWith("-journal") || entry.name.endsWith("-wal")) {
      return true;
    }
  }
  return false;
}

function listCleanupEntries(temporaryDirectory) {
  return readdirSync(temporaryDirectory, { withFileTypes: true })
    .filter((entry) => entry.isDirectory() && entry.name.startsWith(temporaryPrefix))
    .map((entry) => {
      const path = join(temporaryDirectory, entry.name);
      try {
        return {
          name: entry.name,
          modifiedAtMs: statSync(path).mtimeMs,
          hasJournalOrWal: folderContainsJournalOrWal(path),
        };
      } catch (error) {
        return {
          name: entry.name,
          modifiedAtMs: Date.now(),
          hasJournalOrWal: false,
          inspectionError: error.message,
        };
      }
    });
}

function cleanTemporaryFolders({ temporaryDirectory = resolve(tmpdir()), now = Date.now } = {}) {
  const entries = selectCleanupEntries(listCleanupEntries(temporaryDirectory), { now });
  for (const entry of entries) {
    const databasePath = join(temporaryDirectory, entry.name, "test.sqlite3");
    let directoryPath;
    try {
      const validatedDatabasePath = assertIsolatedDatabase(
        `sqlite:///${encodeURI(databasePath.replaceAll("\\", "/"))}`,
      );
      directoryPath = dirname(validatedDatabasePath);
    } catch (error) {
      console.log(`Skipped ${entry.name}: ${error.message}`);
      continue;
    }
    if (entry.inspectionError) {
      console.log(`Skipped ${entry.name}: could not inspect folder (${entry.inspectionError})`);
    } else if (entry.skipReason) {
      console.log(`Skipped ${entry.name}: ${entry.skipReason}`);
    } else {
      rmSync(directoryPath, { recursive: true, force: true });
      console.log(`Removed Playwright temp folder ${directoryPath}`);
    }
  }
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  cleanTemporaryFolders();
}
