import { expect, test } from "@playwright/test";

test("items without a URL render as text while linked items stay linked", async ({
  page,
}) => {
  const pageErrors = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  await page.route("**/api/items/", (route) =>
    route.fulfill({
      json: [
        {
          id: 1,
          title: "Item without a link",
          summary: "Plain title fallback",
          source: "Test feed",
          skills: [],
          estimated_minutes: 10,
          is_low_data: true,
          done: false,
        },
        {
          id: 2,
          title: "Item with a link",
          url: "https://example.test/article",
          summary: "Linked item",
          source: "Test feed",
          skills: [],
          estimated_minutes: 10,
          is_low_data: true,
          done: false,
        },
      ],
    }),
  );

  await page.goto("/items");

  const missingUrlTitle = page.getByRole("heading", {
    name: "Item without a link",
  });
  await expect(missingUrlTitle).toBeVisible();
  await expect(missingUrlTitle.getByRole("link")).toHaveCount(0);

  const linkedTitle = page.getByRole("link", { name: "Item with a link" });
  await expect(linkedTitle).toHaveAttribute(
    "href",
    "https://example.test/article",
  );
  await expect(
    page.getByRole("heading", { name: "Lessons for your pathway" }),
  ).toBeVisible();
  expect(pageErrors).toEqual([]);
});
