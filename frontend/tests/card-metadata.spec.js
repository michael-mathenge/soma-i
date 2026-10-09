import { expect, test } from "@playwright/test";
import { resetE2ESeed } from "./reset-e2e-seed.js";

test.beforeEach(() => resetE2ESeed());

test("lesson cards hide minutes and retain the low data badge", async ({
  page,
}) => {
  await page.route("**/api/items/", (route) =>
    route.fulfill({
      json: [
        {
          id: 1,
          title: "Sample lesson",
          summary: "Short sample summary.",
          source: "SOMA.i sample content",
          skills: ["Spreadsheets"],
          estimated_minutes: 8,
          is_low_data: true,
          done: false,
        },
      ],
    }),
  );

  await page.goto("/items");

  const card = page.locator(".item-card");
  await expect(card).toContainText("SOMA.i sample content");
  await expect(card).toContainText("Low data");
  await expect(card).not.toContainText("8 min");
});
