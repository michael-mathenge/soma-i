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
          excerpt: "Short sample summary.",
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

test("lesson cards link to the publisher and show no excerpt without permission", async ({
  page,
}) => {
  await page.route("**/api/items/", (route) =>
    route.fulfill({
      json: [
        {
          id: 3,
          title: "Publisher lesson",
          url: "https://publisher.example.test/lesson",
          excerpt: "",
          source: "Publisher name",
          skills: ["SQL"],
          estimated_minutes: 8,
          is_low_data: true,
          done: false,
        },
      ],
    }),
  );

  await page.goto("/items");

  const card = page.locator(".item-card");
  // No cleared excerpt, so no excerpt paragraph is rendered at all.
  await expect(card.locator(".item-summary")).toHaveCount(0);
  // The learner is told where the lesson actually is.
  const read = card.getByRole("link", { name: "Read on the publisher's site" });
  await expect(read).toBeVisible();
  await expect(read).toHaveAttribute(
    "href",
    "https://publisher.example.test/lesson",
  );
  await expect(card).toContainText("Publisher name");
});

test("curated reading links show the publisher, the check and the terms", async ({
  page,
}) => {
  await page.route("**/api/items/", (route) =>
    route.fulfill({
      json: [
        {
          id: "curated-7",
          kind: "curated",
          title: "How the web works",
          url: "https://publisher.example.test/how-the-web-works",
          publisher: "MDN Web Docs",
          rationale: "Explains the request and response cycle.",
          reviewed_on: "2026-10-21",
          expires_on: "2026-12-20",
          evidence_url: "https://publisher.example.test/terms",
        },
      ],
    }),
  );

  await page.goto("/items");

  const card = page.locator(".curated-card");
  await expect(card).toHaveCount(1);
  await expect(card).toContainText("Curated reading");
  await expect(card).toContainText("MDN Web Docs");
  await expect(card).toContainText("checked by an editor");
  await expect(card).toContainText("How the web works");
  // A curated link is a reading link, not a stored lesson, so it offers no
  // mark-as-done action.
  await expect(card.getByRole("button", { name: "Mark lesson done" })).toHaveCount(0);
  const read = card.getByRole("link", { name: "Read on the publisher's site" });
  await expect(read).toHaveAttribute(
    "href",
    "https://publisher.example.test/how-the-web-works",
  );
  // The review that cleared the link is disclosed, including the terms.
  await card.getByText("Source details").click();
  await expect(card).toContainText("2026-10-21");
  await expect(
    card.getByRole("link", { name: "Publisher's terms and licence" }),
  ).toHaveAttribute("href", "https://publisher.example.test/terms");
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
          excerpt: "A long summary sentence. ".repeat(60),
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

test("source details expose attribution, dated provenance and unverified rights", async ({
  page,
}) => {
  await page.route("**/api/items/", (route) =>
    route.fulfill({
      json: [
        {
          id: 3,
          title: "Attributed lesson",
          url: "https://publisher.example.test/lesson",
          excerpt: "Offline sample.",
          source: "Fixture publisher",
          source_url: "https://publisher.example.test/feed.xml",
          source_attribution: "Fixture author and publisher",
          source_rights: "CC BY 4.0",
          source_reuse_verified: false,
          content_date: "2026-09-01",
          date_source: "published",
          fetched_at: "2026-10-12T09:00:00+00:00",
          skills: ["SQL"],
          is_low_data: true,
          done: false,
        },
      ],
    }),
  );
  await page.goto("/items");
  const card = page.locator(".item-card");
  const toggle = card.locator(".item-provenance > summary");
  await toggle.focus();
  await page.keyboard.press("Enter");
  await expect(card.locator("details")).toHaveAttribute("open", "");
  await expect(card).toContainText("Fixture author and publisher");
  await expect(card).toContainText("Published");
  await expect(card).toContainText("Retrieved");
  await expect(card.locator("time").nth(0)).toHaveAttribute(
    "datetime",
    "2026-09-01",
  );
  await expect(card.locator("time").nth(1)).toHaveAttribute(
    "datetime",
    "2026-10-12",
  );
  await expect(card).toContainText("CC BY 4.0");
  await expect(card).toContainText("Reuse permission not verified");
  await expect(card.getByRole("link", { name: "Source feed" })).toHaveAttribute(
    "href",
    "https://publisher.example.test/feed.xml",
  );
});

test("retrieval-only and legacy metadata never invent a publication date", async ({
  page,
}) => {
  await page.route("**/api/items/", (route) =>
    route.fulfill({
      json: [
        {
          id: 4,
          title: "Retrieved fixture",
          excerpt: "Offline sample.",
          source: "Fixture publisher",
          source_url: "",
          source_attribution: "",
          source_rights: "",
          content_date: "2026-10-12",
          date_source: "fetched",
          fetched_at: "2026-10-12T09:00:00+00:00",
          skills: [],
          done: false,
        },
        {
          id: 5,
          title: "Legacy fixture",
          excerpt: "Offline sample.",
          source: "Legacy publisher",
          published_at: "2026-10-11T09:00:00+00:00",
          skills: [],
          done: false,
        },
      ],
    }),
  );
  await page.goto("/items");
  const cards = page.locator(".item-card");
  await expect(cards).toHaveCount(2);
  for (const card of await cards.all()) {
    await card.locator("summary").click();
    await expect(card).toContainText("Publication date unavailable");
    await expect(card).toContainText("Attribution unavailable");
    await expect(card).toContainText("Not stated");
    await expect(card).toContainText("Reuse permission not verified");
    await expect(card.getByRole("link", { name: "Source feed" })).toHaveCount(
      0,
    );
  }
  await expect(cards.nth(0).locator("time")).toHaveCount(1);
  await expect(cards.nth(0)).toContainText("Retrieved");
  await expect(cards.nth(1).locator("time")).toHaveCount(0);
  await expect(cards.nth(1)).not.toContainText("2026-10-11");
});

test("updated dates and untrusted attribution stay honest and readable on mobile", async ({
  page,
}) => {
  await page.setViewportSize({ width: 320, height: 800 });
  const attribution = '<img src=x onerror="window.provenanceInjected=true">';
  await page.route("**/api/items/", (route) =>
    route.fulfill({
      json: [
        {
          id: 6,
          title: "Updated fixture",
          excerpt: "Offline sample.",
          source: "Fixture publisher",
          source_attribution: attribution,
          source_rights: "Unverified licence text ".repeat(15),
          content_date: "2026-10-01",
          date_source: "updated",
          fetched_at: "invalid",
          skills: [],
          done: false,
        },
      ],
    }),
  );
  await page.goto("/items");
  const card = page.locator(".item-card");
  await card.locator("summary").click();
  await expect(card).toContainText("Updated");
  await expect(card).not.toContainText("Retrieved");
  await expect(card).toContainText(attribution);
  await expect(card.locator("img")).toHaveCount(0);
  expect(await page.evaluate(() => window.provenanceInjected)).toBeUndefined();
  await expect(card.locator("time")).toHaveAttribute("datetime", "2026-10-01");
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
});

test("source details keep English labels in the experimental Kiswahili interface", async ({
  page,
}) => {
  await page.addInitScript(() => localStorage.setItem("somai-language", "sw"));
  await page.route("**/api/items/", (route) =>
    route.fulfill({
      json: [
        {
          id: 7,
          title: "English fixture",
          excerpt: "Offline sample.",
          source: "Fixture publisher",
          skills: [],
          done: false,
        },
      ],
    }),
  );
  await page.goto("/items");
  await expect(page.locator("html")).toHaveAttribute("lang", "sw");
  await expect(page.locator(".item-provenance")).toHaveAttribute("lang", "en");
  await page.locator(".item-provenance > summary").click();
  await expect(page.locator(".item-card")).toContainText(
    "Publication date unavailable",
  );
  await expect(page.locator(".item-card")).toContainText(
    "Reuse permission not verified",
  );
});
