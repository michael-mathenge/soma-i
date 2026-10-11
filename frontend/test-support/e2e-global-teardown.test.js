import assert from "node:assert/strict";
import { mkdirSync, mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";
import { removeTemporaryDatabase } from "../tests/e2e-global-teardown.js";

function fixture(t) {
  const directory = mkdtempSync(join(tmpdir(), "somai-playwright-teardown-"));
  t.after(() => rmSync(directory, { recursive: true, force: true }));
  return {
    directory,
    url: `sqlite:///${join(directory, "test.sqlite3").replaceAll("\\", "/")}`,
  };
}

test("teardown removes the validated folder on the first attempt", async (t) => {
  const { directory, url } = fixture(t);
  const calls = [];
  await removeTemporaryDatabase(url, {
    remove: (...args) => calls.push(args),
    wait: () => assert.fail("unexpected retry"),
    warn: () => assert.fail("unexpected warning"),
  });
  assert.deepEqual(calls, [[directory, { recursive: true, force: true }]]);
});

for (const code of ["EBUSY", "EPERM", "ENOTEMPTY"]) {
  test(`teardown retries ${code} and succeeds without warning`, async (t) => {
    const { url } = fixture(t);
    let attempts = 0;
    const delays = [];
    await removeTemporaryDatabase(url, {
      remove: () => {
        if (++attempts < 4) throw Object.assign(new Error(code), { code });
      },
      wait: async (delay) => {
        delays.push(delay);
      },
      warn: () => assert.fail("unexpected warning"),
    });
    assert.equal(attempts, 4);
    assert.deepEqual(delays, [100, 100, 100]);
  });

  test(`teardown warns and resolves after four ${code} failures`, async (t) => {
    const { directory, url } = fixture(t);
    let attempts = 0;
    const delays = [];
    const warnings = [];
    await removeTemporaryDatabase(url, {
      remove: () => {
        attempts += 1;
        throw Object.assign(new Error(code), { code });
      },
      wait: async (delay) => {
        delays.push(delay);
      },
      warn: (message) => warnings.push(message),
    });
    assert.equal(attempts, 4);
    assert.deepEqual(delays, [100, 100, 100]);
    assert.deepEqual(warnings, [
      `Temporary Playwright database remains at ${directory}`,
    ]);
  });
}

test("teardown rethrows unexpected errors without retrying", async (t) => {
  const { url } = fixture(t);
  const error = Object.assign(new Error("denied"), { code: "EACCES" });
  let attempts = 0;
  await assert.rejects(
    removeTemporaryDatabase(url, {
      remove: () => {
        attempts += 1;
        throw error;
      },
      wait: () => assert.fail("unexpected retry"),
      warn: () => assert.fail("unexpected warning"),
    }),
    (actual) => actual === error,
  );
  assert.equal(attempts, 1);
});

test("teardown skips an absent database URL", async () => {
  await removeTemporaryDatabase(undefined, {
    remove: () => assert.fail("unexpected removal"),
  });
});

test("teardown rejects unsafe paths before removal", async (t) => {
  const { directory } = fixture(t);
  const nested = join(directory, "nested");
  mkdirSync(nested);
  const paths = [
    join(tmpdir(), "test.sqlite3"),
    join(directory, "other.sqlite3"),
    join(nested, "test.sqlite3"),
  ];
  for (const path of paths) {
    await assert.rejects(
      removeTemporaryDatabase(`sqlite:///${path.replaceAll("\\", "/")}`, {
        remove: () => assert.fail("unsafe removal"),
      }),
    );
  }
});

test("teardown revalidates the path before retrying", async (t) => {
  const { directory, url } = fixture(t);
  let attempts = 0;
  await assert.rejects(
    removeTemporaryDatabase(url, {
      remove: () => {
        attempts += 1;
        throw Object.assign(new Error("busy"), { code: "EBUSY" });
      },
      wait: async () => rmSync(directory, { recursive: true, force: true }),
      warn: () => assert.fail("unexpected warning"),
    }),
  );
  assert.equal(attempts, 1);
});
