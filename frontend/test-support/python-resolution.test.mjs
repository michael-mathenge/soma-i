import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { existsSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import { resolvePython } from "../../backend/python-resolution.mjs";

const isWindows = process.platform === "win32";

test("Python resolution uses only existing files in priority order", (t) => {
  const directory = mkdtempSync(join(tmpdir(), "somai-python-resolution-"));
  t.after(() => rmSync(directory, { recursive: true, force: true }));
  const override = join(directory, "override.exe");
  const venv = join(directory, "python.exe");
  const missing = join(directory, "missing.exe");
  writeFileSync(override, "");
  writeFileSync(venv, "");
  assert.equal(resolvePython(override, venv), override);
  assert.equal(resolvePython(directory, venv), venv);
  assert.equal(resolvePython(missing, venv), venv);
  assert.equal(resolvePython("", venv), venv);
  assert.equal(resolvePython(undefined, venv), venv);
  assert.equal(resolvePython(directory, missing), "py");
  assert.equal(resolvePython(missing, directory), "py");
});

test("child ignores a folder PYTHON and starts the selected interpreter", (t) => {
  const resolver = new URL("../../backend/python-resolution.mjs", import.meta.url);
  // The virtual environment layout differs by platform, so the test resolves
  // the interpreter the same way the application does.
  const venv = isWindows
    ? new URL("../../.venv/Scripts/python.exe", import.meta.url)
    : new URL("../../.venv/bin/python", import.meta.url);
  const folder = new URL("../../backend/", import.meta.url);
  if (!existsSync(fileURLToPath(venv))) {
    t.skip(
      `no virtual environment at ${fileURLToPath(venv)}; run the suite from a prepared checkout`,
    );
    return;
  }
  const source = `
    import { spawnSync } from "node:child_process";
    import { fileURLToPath } from "node:url";
    import { resolvePython } from ${JSON.stringify(resolver.href)};
    const selected = resolvePython(
      process.env.PYTHON, fileURLToPath(new URL(${JSON.stringify(venv.href)})));
    console.log(selected);
    const result = spawnSync(selected,
      selected === "py" ? ["-3.12", "--version"] : ["--version"],
      { encoding: "utf8" });
    process.stdout.write(result.stdout || "");
    process.stderr.write(result.stderr || "");
    process.exit(result.status ?? 1);
  `;
  const result = spawnSync(process.execPath, ["--input-type=module", "-e", source], {
    env: { ...process.env, PYTHON: fileURLToPath(folder) },
    encoding: "utf8",
  });
  assert.equal(result.status, 0, result.stderr);
  assert.equal(result.stdout.split(/\r?\n/)[0], fileURLToPath(venv));
  assert.match(result.stdout + result.stderr, /Python \d+\.\d+/);
});
