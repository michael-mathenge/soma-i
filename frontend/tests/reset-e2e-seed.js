import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const testsDirectory = dirname(fileURLToPath(import.meta.url));
const repositoryRoot = resolve(testsDirectory, "../..");
const backendDirectory = resolve(repositoryRoot, "backend");
const python =
  process.env.PYTHON || resolve(repositoryRoot, ".venv", "Scripts", "python.exe");

export function resetE2ESeed() {
  const databaseUrl = process.env.SOMAI_E2E_DATABASE_URL;
  if (!databaseUrl?.startsWith("sqlite:///")) {
    throw new Error("Playwright must use its isolated temporary SQLite database.");
  }
  console.log(`Resetting fresh Playwright seed in ${databaseUrl}`);
  for (const args of [
    ["flush", "--noinput"],
    ["seed_demo"],
  ]) {
    const result = spawnSync(
      python,
      [resolve(backendDirectory, "manage.py"), ...args],
      {
        cwd: backendDirectory,
        env: {
          ...process.env,
          DATABASE_URL: databaseUrl,
        },
        encoding: "utf8",
      },
    );
    if (result.status !== 0) {
      throw new Error(result.stderr || result.stdout || `Failed: ${args.join(" ")}`);
    }
  }
}
