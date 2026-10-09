import assert from "node:assert/strict";
import { test } from "node:test";
import { join, resolve } from "node:path";
import { tmpdir } from "node:os";

import { assertIsolatedDatabase } from "./e2e-database-guard.js";

const repositoryRoot = resolve(import.meta.dirname, "../..");

function sqliteUrl(databasePath, shouldResolve = true) {
  const path = shouldResolve ? resolve(databasePath) : databasePath;
  return `sqlite:///${path.replaceAll("\\", "/")}`;
}

test("rejects the project database path", () => {
  const projectDatabase = join(repositoryRoot, "backend", "db.sqlite3");
  assert.throws(
    () => assertIsolatedDatabase(sqliteUrl(projectDatabase)),
    /must never use backend\/db\.sqlite3/,
  );
});

test("rejects the repository-root database path", () => {
  const projectDatabase = join(repositoryRoot, "db.sqlite3");
  assert.throws(
    () => assertIsolatedDatabase(sqliteUrl(projectDatabase)),
    /must never use backend\/db\.sqlite3 or repository-root db\.sqlite3/,
  );
});

test(
  "rejects a case-variant project database path on Windows",
  { skip: process.platform !== "win32" },
  () => {
    const projectDatabase = join(repositoryRoot, "BACKEND", "DB.SQLITE3");
    assert.throws(
      () => assertIsolatedDatabase(sqliteUrl(projectDatabase)),
      /must never use backend\/db\.sqlite3/,
    );
  },
);

test(
  "rejects a case-variant repository-root database path on Windows",
  { skip: process.platform !== "win32" },
  () => {
    const projectDatabase = join(repositoryRoot, "DB.SQLITE3");
    assert.throws(
      () => assertIsolatedDatabase(sqliteUrl(projectDatabase)),
      /repository-root db\.sqlite3/,
    );
  },
);

test("rejects an empty database URL", () => {
  assert.throws(
    () => assertIsolatedDatabase(""),
    /requires a SQLite database URL/,
  );
});

test("rejects a SQLite file outside the OS temp directory", () => {
  assert.throws(
    () =>
      assertIsolatedDatabase(
        sqliteUrl(join(repositoryRoot, "outside.sqlite3")),
      ),
    /inside the OS temp directory/,
  );
});

test("rejects a file in a temp folder without the required prefix", () => {
  assert.throws(
    () =>
      assertIsolatedDatabase(
        sqliteUrl(join(tmpdir(), "ordinary-temp-folder", "test.sqlite3")),
      ),
    /somai-playwright-/,
  );
});

test("rejects a file name other than test.sqlite3", () => {
  assert.throws(
    () =>
      assertIsolatedDatabase(
        sqliteUrl(
          join(tmpdir(), "somai-playwright-guard-test", "items.sqlite3"),
        ),
      ),
    /file must be named test\.sqlite3/,
  );
});

test("rejects a .. traversal even when the raw path starts with the temp prefix", () => {
  const traversalPath = `${tmpdir().replaceAll("\\", "/")}/somai-playwright-escape/../../outside/test.sqlite3`;
  assert.throws(
    () => assertIsolatedDatabase(sqliteUrl(traversalPath, false)),
    /inside the OS temp directory/,
  );
});

test("rejects percent-encoded traversal after decoding", () => {
  const encodedTraversal = `${tmpdir().replaceAll("\\", "/")}/somai-playwright-encoded/%2e%2e/outside/test.sqlite3`;
  assert.throws(() =>
    assertIsolatedDatabase(sqliteUrl(encodedTraversal, false)),
  );
});

test("rejects the project database path with a trailing dot", () => {
  const projectDatabase = `${join(repositoryRoot, "backend", "db.sqlite3")}.`;
  assert.throws(
    () => assertIsolatedDatabase(sqliteUrl(projectDatabase)),
    /trailing dots or spaces/,
  );
});

test("rejects the project database path with a trailing space", () => {
  const projectDatabase = `${join(repositoryRoot, "backend", "db.sqlite3")} `;
  assert.throws(
    () => assertIsolatedDatabase(sqliteUrl(projectDatabase)),
    /trailing dots or spaces/,
  );
});

test("rejects a non-SQLite URL", () => {
  assert.throws(
    () => assertIsolatedDatabase("postgresql://localhost/somai"),
    /requires a SQLite database URL/,
  );
});

test("rejects a missing database URL", () => {
  assert.throws(
    () => assertIsolatedDatabase(undefined),
    /requires a SQLite database URL/,
  );
});

test("accepts a database under a somai-playwright temp folder", () => {
  const databasePath = join(
    tmpdir(),
    "somai-playwright-guard-test",
    "test.sqlite3",
  );
  assert.equal(
    assertIsolatedDatabase(sqliteUrl(databasePath)),
    resolve(databasePath),
  );
});

test("allows nesting below the first somai-playwright-* temp folder", () => {
  const databasePath = join(
    tmpdir(),
    "somai-playwright-nested-test",
    "sub",
    "test.sqlite3",
  );
  assert.equal(
    assertIsolatedDatabase(sqliteUrl(databasePath)),
    resolve(databasePath),
  );
});
