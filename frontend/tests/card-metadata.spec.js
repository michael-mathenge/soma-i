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

test("long lesson summaries clamp to four lines with an ellipsis", async ({
  page,
}) => {
  await page.route("**/api/items/", (route) =>
    route.fulfill({
      json: [
        {
          id: 2,
          title: "Long summary lesson",
          summary: "A long summary sentence. ".repeat(60),
          source: "Sample source",
          skills: ["CSS"],
          estimated_minutes: 8,
          is_low_data: true,
          done: false,
        },
      ],
    }),
  );

  await page.goto("/items");

  const summary = page.locator(".item-summary");
  await expect(summary).toBeVisible();
  await expect
    .poll(() =>
      summary.evaluate((element) => {
        const style = getComputedStyle(element);
        return {
          clamp: style.webkitLineClamp,
          orient: style.webkitBoxOrient,
          overflow: style.overflow,
          clipped: element.scrollHeight > element.clientHeight,
        };
      }),
    )
    .toEqual({
      clamp: "4",
      orient: "vertical",
      overflow: "hidden",
      clipped: true,
    });
});
