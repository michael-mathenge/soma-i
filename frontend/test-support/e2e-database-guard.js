import { fileURLToPath } from "node:url";
import {
  basename,
  dirname,
  isAbsolute,
  relative,
  resolve,
  sep,
} from "node:path";
import { existsSync, realpathSync } from "node:fs";
import { tmpdir } from "node:os";

const testsDirectory = dirname(fileURLToPath(import.meta.url));
const repositoryRoot = resolve(testsDirectory, "../..");
const backendDatabasePath = resolve(repositoryRoot, "backend", "db.sqlite3");
const repositoryDatabasePath = resolve(repositoryRoot, "db.sqlite3");
const defaultProjectDatabasePaths = [backendDatabasePath, repositoryDatabasePath];
const temporaryDirectory = resolve(tmpdir());
const temporaryPrefix = "somai-playwright-";

function isInside(directory, filePath) {
  const relativePath = relative(directory, filePath);
  return (
    relativePath !== ".." &&
    !relativePath.startsWith(`..${sep}`) &&
    !isAbsolute(relativePath)
  );
}

function samePath(left, right) {
  return process.platform === "win32"
    ? left.toLowerCase() === right.toLowerCase()
    : left === right;
}

export function assertIsolatedDatabase(
  databaseUrl,
  { projectDatabasePaths = defaultProjectDatabasePaths } = {},
) {
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

  const projectPathMatch = defaultProjectDatabasePaths.some((projectPath) =>
    samePath(projectPath, databasePath),
  );
  if (projectPathMatch) {
    throw new Error(
      "Playwright must never use backend/db.sqlite3 or repository-root db.sqlite3.",
    );
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

  const realTemporaryDirectory = realpathSync(temporaryDirectory);
  const realParentDirectory = realpathSync(dirname(databasePath));
  const realDatabasePath = existsSync(databasePath)
    ? realpathSync(databasePath)
    : resolve(realParentDirectory, basename(databasePath));
  const realProjectDatabasePaths = projectDatabasePaths.map((projectPath) =>
    existsSync(projectPath) ? realpathSync(projectPath) : resolve(projectPath),
  );
  if (
    !isInside(realTemporaryDirectory, realParentDirectory) ||
    !isInside(realTemporaryDirectory, realDatabasePath)
  ) {
    throw new Error(
      "Playwright SQLite database must resolve inside the OS temp directory.",
    );
  }
  if (
    realProjectDatabasePaths.some((projectPath) =>
      samePath(projectPath, realDatabasePath),
    )
  ) {
    throw new Error(
      "Playwright must never use backend/db.sqlite3 or repository-root db.sqlite3.",
    );
  }

  return databasePath;
}
