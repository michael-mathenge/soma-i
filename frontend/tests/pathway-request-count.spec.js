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

test("unauthenticated refresh reuses the original pathways request after a 401", async ({
  page,
}) => {
  const pathwayRequests = watchPathwayRequests(page);
  await page.route("**/api/me/", (route) =>
    route.fulfill({ status: 401, json: { detail: "Authentication required." } }),
  );
  await page.route("**/api/pathways/", (route) =>
    route.fulfill({
      json: [
        {
          id: 1,
          title: "Data Analyst",
          target_outcome: "Junior Data Analyst",
        },
      ],
    }),
  );

  await page.goto("/");

  await expect(
    page.getByLabel("Learning pathway").locator("option").filter({
      hasText: /Data Analyst/,
    }),
  ).toHaveCount(1);
  expect(pathwayRequests).toHaveLength(1);
});

test("refresh retries a failed pathways request once", async ({ page }) => {
  const pathwayRequests = watchPathwayRequests(page);
  let attempts = 0;
  await page.route("**/api/me/", (route) =>
    route.fulfill({ status: 401, json: { detail: "Authentication required." } }),
  );
  await page.route("**/api/pathways/", (route) => {
    attempts += 1;
    if (attempts === 1) {
      return route.fulfill({ status: 503, json: { detail: "Unavailable." } });
    }
    return route.fulfill({
      json: [
        {
          id: 1,
          title: "Data Analyst",
          target_outcome: "Junior Data Analyst",
        },
      ],
    });
  });

  await page.goto("/");

  await expect(
    page.getByLabel("Learning pathway").locator("option").filter({
      hasText: /Data Analyst/,
    }),
  ).toHaveCount(1);
  expect(pathwayRequests).toHaveLength(2);
});

test("refresh retries a failed pathways request once and settles if it fails again", async ({
  page,
}) => {
  const pathwayRequests = watchPathwayRequests(page);
  const pageErrors = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  await page.route("**/api/me/", (route) =>
    route.fulfill({ status: 401, json: { detail: "Authentication required." } }),
  );
  await page.route("**/api/pathways/", (route) =>
    route.fulfill({ status: 503, json: { detail: "Unavailable." } }),
  );

  await page.goto("/");

  await expect(
    page.getByRole("heading", { name: "Choose a pathway" }),
  ).toBeVisible();
  await expect(
    page.getByLabel("Learning pathway").locator("option"),
  ).toHaveCount(1);
  expect(pathwayRequests).toHaveLength(2);
  expect(pageErrors).toEqual([]);
});
