import { spawnSync } from "node:child_process";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test } from "@playwright/test";
import { assertIsolatedDatabase } from "../test-support/e2e-database-guard.js";
import { resetE2ESeed } from "./reset-e2e-seed.js";

const testsDirectory = dirname(fileURLToPath(import.meta.url));
const repositoryRoot = resolve(testsDirectory, "../..");
const backendDirectory = resolve(repositoryRoot, "backend");
const python =
  process.env.PYTHON || resolve(repositoryRoot, ".venv", "Scripts", "python.exe");

function loadDeclaredSeedPicks() {
  const databaseUrl = process.env.SOMAI_E2E_DATABASE_URL;
  const databasePath = assertIsolatedDatabase(databaseUrl);
  const validatedDatabaseUrl = `sqlite:///${databasePath.replaceAll("\\", "/")}`;
  const result = spawnSync(
    python,
    [resolve(backendDirectory, "manage.py"), "dump_seed_picks"],
    {
      cwd: backendDirectory,
      env: { ...process.env, DATABASE_URL: validatedDatabaseUrl },
      encoding: "utf8",
    },
  );
  if (result.status !== 0) {
    throw new Error(result.stderr || result.stdout || "Failed to dump seed picks.");
  }
  return JSON.parse(result.stdout);
}

test("dashboard cards use seeded picks for each remaining skill", async ({
  page,
  request,
}) => {
  const declaredPicks = loadDeclaredSeedPicks();
  const pathwaysResponse = await request.get("/api/pathways/");
  expect(pathwaysResponse.ok()).toBeTruthy();
  const pathways = await pathwaysResponse.json();
  const cardsByPathway = new Map();

  for (const pathway of pathways) {
    await resetE2ESeed();
    await page.context().clearCookies();
    await page.goto("/");
    await page.getByLabel("Learning pathway").selectOption(String(pathway.id));
    await page.getByLabel("Name (optional)").fill("Pathway pick test");

    const dashboardResponse = page.waitForResponse(
      (response) =>
        response.url().endsWith("/api/dashboard/") && response.status() === 200,
    );
    await page.getByRole("button", { name: "Start learning" }).click();

    await expect(
      page.getByRole("heading", { name: pathway.title }),
    ).toBeVisible();
    const dashboard = await (await dashboardResponse).json();
    const cardHeadings = page.locator(".cards .item-card h3");
    await expect(cardHeadings).toHaveCount(dashboard.items.length);
    const visibleTitles = await cardHeadings.allTextContents();
    const dashboardTitles = dashboard.items.map((item) => item.title);
    expect([...visibleTitles].sort()).toEqual([...dashboardTitles].sort());

    const remainingSkills = dashboard.remaining;
    const declaredIds = new Set(
      remainingSkills.flatMap((skill) =>
        (declaredPicks[pathway.title]?.[skill] ?? []).map((pick) => pick.id),
      ),
    );
    for (const item of dashboard.items) {
      expect(declaredIds.has(item.id)).toBeTruthy();
    }

    for (const skill of remainingSkills) {
      const declaredForSkill = declaredPicks[pathway.title]?.[skill] ?? [];
      if (declaredForSkill.length === 0) continue;
      const expectedIds = new Set(declaredForSkill.map((pick) => pick.id));
      expect(
        dashboard.items.some(
          (item) => item.skills.includes(skill) && expectedIds.has(item.id),
        ),
        `${pathway.title} should show a seeded pick for ${skill}`,
      ).toBeTruthy();
    }

    cardsByPathway.set(pathway.title, new Set(visibleTitles));
  }

  const frontendTitles = cardsByPathway.get("Frontend Developer");
  const backendTitles = cardsByPathway.get("Backend/Python Developer");
  expect([...frontendTitles].sort()).not.toEqual([...backendTitles].sort());
});
