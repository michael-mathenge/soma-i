import { expect, test } from "@playwright/test";
import { resetE2ESeed } from "./reset-e2e-seed.js";

test("dashboard cards use seeded picks for each remaining skill", async ({
  page,
  request,
}) => {
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
    const declaredUrls = new Set(
      remainingSkills.flatMap((skill) =>
        (pathway.seeded_picks[skill] ?? []).map((pick) => pick.url),
      ),
    );
    for (const item of dashboard.items) {
      expect(declaredUrls.has(item.url)).toBeTruthy();
    }

    for (const skill of remainingSkills) {
      const declaredForSkill = pathway.seeded_picks[skill] ?? [];
      if (declaredForSkill.length === 0) continue;
      const expectedUrls = new Set(declaredForSkill.map((pick) => pick.url));
      expect(
        dashboard.items.some(
          (item) => item.skills.includes(skill) && expectedUrls.has(item.url),
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
