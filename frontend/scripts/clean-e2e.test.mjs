import assert from "node:assert/strict";
import { test } from "node:test";

import { selectCleanupEntries } from "./clean-e2e.mjs";

test("keeps recent and active databases, selects only old idle folders", () => {
  const now = 1_800_000_000_000;
  const entries = selectCleanupEntries(
    [
      {
        name: "somai-playwright-recent",
        modifiedAtMs: now - 9 * 60 * 1000,
        hasJournalOrWal: false,
      },
      {
        name: "somai-playwright-active",
        modifiedAtMs: now - 30 * 60 * 1000,
        hasJournalOrWal: true,
      },
      {
        name: "somai-playwright-idle",
        modifiedAtMs: now - 11 * 60 * 1000,
        hasJournalOrWal: false,
      },
      {
        name: "unrelated-temp-folder",
        modifiedAtMs: now - 60 * 60 * 1000,
        hasJournalOrWal: false,
      },
    ],
    { now: () => now },
  );

  assert.deepEqual(
    entries.map(({ name, skipReason }) => [name, skipReason]),
    [
      ["somai-playwright-recent", "modified in the last 10 minutes"],
      ["somai-playwright-active", "contains a SQLite -journal or -wal file"],
      ["somai-playwright-idle", null],
    ],
  );
});
