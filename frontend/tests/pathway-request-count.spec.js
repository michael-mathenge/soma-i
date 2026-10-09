import { expect, test } from "@playwright/test";
import { resetE2ESeed } from "./reset-e2e-seed.js";

test.beforeEach(() => resetE2ESeed());

function watchPathwayRequests(page) {
  const requests = [];
  page.on("request", (request) => {
    if (new URL(request.url()).pathname.endsWith("/api/pathways/")) {
      requests.push(request.url());
    }
  });
  return requests;
}

test("unauthenticated page loads request pathways at least once and at most twice", async ({
  page,
}) => {
  const pathwayRequests = watchPathwayRequests(page);

  await page.goto("/pathway");
  await expect(page.getByText("Choose a pathway to get started.")).toBeVisible();
  await page.waitForLoadState("networkidle");

  expect(pathwayRequests.length).toBeGreaterThanOrEqual(1);
  expect(pathwayRequests.length).toBeLessThanOrEqual(2);
});

test("signed-in dashboard requests pathways at most once", async ({ page }) => {
  const pathwayRequests = watchPathwayRequests(page);

  await page.goto("/");
  const pathwaySelect = page.getByLabel("Learning pathway");
  const pathwayOption = pathwaySelect
    .locator("option")
    .filter({ hasText: /Data Analyst/ })
    .first();
  await pathwaySelect.selectOption(await pathwayOption.getAttribute("value"));
  await page.getByRole("button", { name: "Start learning" }).click();
  await expect(
    page.getByRole("heading", { name: "Data Analyst" }),
  ).toBeVisible();

  pathwayRequests.length = 0;
  await page.goto("/pathway");
  await expect(page.getByRole("heading", { name: "Data Analyst" })).toBeVisible();
  await page.waitForLoadState("networkidle");

  expect(pathwayRequests.length).toBeLessThanOrEqual(1);
});
