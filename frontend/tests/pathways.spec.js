import { expect, test } from "@playwright/test";
import { resetE2ESeed } from "./reset-e2e-seed.js";

test.beforeEach(() => resetE2ESeed());

test("Learning pathway selector lists exactly the three pathways", async ({
  page,
  request,
}) => {
  await page.goto("/");
  const response = await request.get("/api/pathways/");
  expect(response.ok()).toBeTruthy();
  const pathways = await response.json();
  expect(pathways).toHaveLength(3);

  const selector = page.getByLabel("Learning pathway");
  const selectorOptions = selector.locator("option");
  await expect(selectorOptions).toHaveCount(pathways.length + 1);
  const options = await selectorOptions
    .evaluateAll((all) =>
      all
        .filter((option) => option.value)
        .map((option) => option.textContent.trim()),
    );
  expect(options).toEqual(
    pathways.map((pathway) => `${pathway.title} · ${pathway.target_outcome}`),
  );
});

for (const pathwayIndex of [0, 1, 2]) {
  test(`pathway ${pathwayIndex + 1} shows at least one pick`, async ({
    page,
    request,
  }) => {
    const response = await request.get("/api/pathways/");
    expect(response.ok()).toBeTruthy();
    const pathways = await response.json();
    const pathway = pathways[pathwayIndex];
    expect(pathway).toBeTruthy();

    await page.goto("/");
    await page
      .getByLabel("Learning pathway")
      .selectOption(String(pathway.id));
    await page.getByLabel("Name (optional)").fill("Pathway smoke test");
    await page.getByRole("button", { name: "Start learning" }).click();

    await expect(page.getByRole("heading", { name: pathway.title })).toBeVisible();
    await expect(page.locator(".cards .item-card").first()).toBeVisible();
  });
}
