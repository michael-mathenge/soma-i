import { fileURLToPath } from "node:url";
import {
  basename,
  dirname,
  isAbsolute,
  relative,
  resolve,
  sep,
} from "node:path";
import { tmpdir } from "node:os";

const testsDirectory = dirname(fileURLToPath(import.meta.url));
const repositoryRoot = resolve(testsDirectory, "../..");
const backendDatabasePath = resolve(repositoryRoot, "backend", "db.sqlite3");
const temporaryDirectory = resolve(tmpdir());
const temporaryPrefix = "somai-playwright-";

export function assertIsolatedDatabase(databaseUrl) {
  if (
    typeof databaseUrl !== "string" ||
    databaseUrl.length === 0 ||
    !databaseUrl.startsWith("sqlite:///")
  ) {
    throw new Error("Playwright requires a SQLite database URL.");
  }

  const encodedPath = databaseUrl
    .slice("sqlite:///".length)
    .split(/[?#]/, 1)[0];
  if (!encodedPath) {
    throw new Error("Playwright SQLite URL must include a database file path.");
  }

  let databasePath;
  try {
    databasePath = decodeURIComponent(encodedPath);
  } catch {
    throw new Error("Playwright SQLite URL contains an invalid encoded path.");
  }
  if (
    databasePath
      .split(/[\\/]/)
      .some((part) => part !== "." && part !== ".." && /[. ]$/.test(part))
  ) {
    throw new Error(
      "Playwright SQLite database path cannot contain trailing dots or spaces.",
    );
  }
  databasePath = isAbsolute(databasePath)
    ? resolve(databasePath)
    : resolve(repositoryRoot, databasePath);

  const projectPathMatch =
    process.platform === "win32"
      ? backendDatabasePath.toLowerCase() === databasePath.toLowerCase()
      : backendDatabasePath === databasePath;
  if (projectPathMatch) {
    throw new Error("Playwright must never use backend/db.sqlite3.");
  }

  const relativeToTemp = relative(temporaryDirectory, databasePath);
  if (
    !relativeToTemp ||
    relativeToTemp === ".." ||
    relativeToTemp.startsWith(`..${sep}`) ||
    isAbsolute(relativeToTemp)
  ) {
    throw new Error(
      "Playwright SQLite database must be inside the OS temp directory.",
    );
  }

  if (basename(databasePath) !== "test.sqlite3") {
    throw new Error(
      "Playwright SQLite database file must be named test.sqlite3.",
    );
  }

  const firstFolderUnderTemp = relativeToTemp.split(sep)[0];
  if (
    !firstFolderUnderTemp.startsWith(temporaryPrefix) ||
    firstFolderUnderTemp.length === temporaryPrefix.length
  ) {
    throw new Error(
      'Playwright SQLite database must be under a "somai-playwright-*" folder.',
    );
  }

  return databasePath;
}
