import { expect, test } from "@playwright/test";
test.use({ serviceWorkers: "block" });
const topics = Array.from({ length: 13 }, (_, index) => ({
  slug: `topic-${index + 1}`,
  title: `Topic ${index + 1}`,
  description: "Offline topic fixture",
  target_outcome: "Practice independently",
  available: true,
  available_pathway_id: index + 1,
  is_demo: true,
  version: 1,
  image: {
    url: "https://images.example.test/topic.jpg",
    alt: "Topic illustration",
    credit: "Unsplash",
  },
  steps: [
    {
      skill: `Skill ${index + 1} A`,
      title: "Check A",
      criteria: "Example",
      requires: [],
    },
    {
      skill: `Skill ${index + 1} B`,
      title: "Check B",
      criteria: "Example",
      requires: [],
    },
  ],
}));
async function fixtures(page, handler) {
  // The served queries are recorded so a test can wait for the request it
  // triggered instead of asserting on a render that follows it.
  const served = [];
  await page.route("**/api/**", async (route) => {
    const url = new URL(route.request().url());
    if (route.request().method() !== "GET") return route.abort();
    if (url.pathname === "/api/me/")
      return route.fulfill({ status: 401, json: {} });
    // The onboarding select is fed by the legacy pathway list.
    if (url.pathname === "/api/pathways/")
      return route.fulfill({
        json: topics.map((topic) => ({
          id: topic.available_pathway_id,
          title: topic.title,
          description: topic.description,
          target_outcome: topic.target_outcome,
          locale: "KE",
        })),
      });
    if (url.pathname !== "/api/roadmaps/") return route.abort();
    if (!url.searchParams.has("page")) return route.fulfill({ json: topics });
    if (handler && (await handler(route, url))) return;
    const query = url.searchParams.get("q") || "";
    const number = Number(url.searchParams.get("page"));
    const matches = topics.filter((topic) =>
      topic.title.toLowerCase().includes(query.toLowerCase()),
    );
    served.push({ query, page: number, count: matches.length });
    return route.fulfill({
      json: {
        results: matches.slice((number - 1) * 12, number * 12),
        count: matches.length,
        page: number,
        page_size: 12,
        has_next: number * 12 < matches.length,
      },
    });
  });
  return served;
}
test("catalogue pages preserve URL history and selected onboarding pathway", async ({
  page,
}) => {
  const initialRequests = [];
  page.on("request", (request) => initialRequests.push(new URL(request.url())));
  await fixtures(page);
  await page.goto("/catalogue");
  await expect(page.getByRole("article")).toHaveCount(12);
  expect(
    initialRequests.filter(
      (url) =>
        url.pathname === "/api/roadmaps/" && !url.searchParams.has("page"),
    ),
  ).toHaveLength(0);
  expect(
    initialRequests.filter((url) => url.pathname === "/api/me/"),
  ).toHaveLength(0);
  await expect(
    page.getByRole("button", { name: "Previous page" }),
  ).toBeDisabled();
  await page.getByRole("button", { name: "Next page" }).click();
  await expect(page).toHaveURL(/page=2/);
  await expect(page.getByRole("article")).toHaveCount(1);
  await expect(page.getByText("Demo topic", { exact: true })).toBeVisible();
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Topic 13", exact: true }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Choose a pathway: Topic 13" }).click();
  await expect(
    page.getByRole("combobox", { name: "Learning pathway", exact: true }),
  ).toHaveValue("13");
  await page.goBack();
  await expect(
    page.getByRole("heading", { name: "Topic 13", exact: true }),
  ).toBeVisible();
});
test("catalogue search submits explicitly resets pages and handles empty results", async ({
  page,
}) => {
  const served = await fixtures(page);
  await page.goto("/catalogue?page=2");
  const search = page.getByRole("searchbox", { name: "Search topics" });
  await search.fill("Topic 2");
  await expect(page).toHaveURL(/page=2/);
  await search.press("Enter");
  await expect(page.getByRole("article")).toHaveCount(1);
  await expect(page).toHaveURL(/page=1/);
  await search.fill("missing");
  await search.press("Enter");
  // Wait for the second search to reach the server before asserting the
  // empty result. Asserting the render alone can observe the previous
  // result set on a slower machine.
  await expect
    .poll(() => served.filter((entry) => entry.query === "missing").length, {
      message: () =>
        `served=${JSON.stringify(served)} url=${page.url()} input=${search.inputValue()}`,
    })
    .toBe(1);
  await expect(page.getByText(/No topics on this page/)).toBeVisible();
  await page.getByRole("button", { name: "Clear search" }).click();
  await expect(page.getByRole("article")).toHaveCount(12);
  await expect(search).toHaveValue("");
});
test("catalogue errors retry and loading does not expose old cards", async ({
  page,
}) => {
  let fail = true;
  await fixtures(page, async (route) => {
    if (!fail) return false;
    await route.fulfill({ status: 503, json: {} });
    return true;
  });
  await page.goto("/catalogue");
  await expect(page.getByRole("alert")).toContainText(
    "Topics could not be loaded",
  );
  await expect(page.getByRole("article")).toHaveCount(0);
  fail = false;
  await page.getByRole("button", { name: "Retry" }).click();
  await expect(page.getByRole("article")).toHaveCount(12);
});
test("catalogue narrow keyboard navigation and English language marking", async ({
  page,
}) => {
  await fixtures(page);
  await page.addInitScript(() => localStorage.setItem("somai-language", "sw"));
  await page.setViewportSize({ width: 320, height: 800 });
  await page.goto("/catalogue?page=invalid");
  const heading = page.getByRole("heading", { name: "Explore topics" });
  await expect(heading).toBeVisible();
  await expect(heading.locator("..")).not.toHaveAttribute("lang", "sw");
  await expect(heading.locator("../..")).toHaveAttribute("lang", "en");
  await expect(page.getByRole("article")).toHaveCount(12);
  const search = page.getByRole("searchbox");
  await search.focus();
  await page.keyboard.press("Tab");
  await expect(
    page.getByRole("button", { name: "Search", exact: true }),
  ).toBeFocused();
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth),
  ).toBeLessThanOrEqual(320);
});
test("catalogue marks a roadmap without an open pathway as a preview", async ({
  page,
}) => {
  await page.route("**/api/**", async (route) => {
    const url = new URL(route.request().url());
    if (route.request().method() !== "GET") return route.abort();
    if (url.pathname === "/api/me/")
      return route.fulfill({ status: 401, json: {} });
    if (url.pathname !== "/api/roadmaps/") return route.abort();
    return route.fulfill({
      json: {
        results: [
          {
            slug: "locked-topic",
            title: "Locked topic",
            description: "Not open for enrollment",
            target_outcome: "Practice independently",
            available: false,
            available_pathway_id: null,
            is_demo: false,
            version: null,
            image: {},
            steps: [
              {
                skill: "Locked skill",
                title: "Check",
                criteria: "Example",
                requires: [],
              },
            ],
          },
        ],
        count: 1,
        page: 1,
        page_size: 12,
        has_next: false,
      },
    });
  });
  await page.goto("/catalogue");
  await expect(page.getByRole("article")).toHaveCount(1);
  await expect(
    page.getByText("Roadmap preview", { exact: true }),
  ).toBeVisible();
  await expect(page.getByText(/not open for enrollment yet/)).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Choose a pathway: Locked topic" }),
  ).toHaveCount(0);
  await expect(page.getByRole("list")).toBeVisible();
});
test("catalogue ignores a superseded delayed response", async ({ page }) => {
  let release;
  const waiting = new Promise((resolve) => {
    release = resolve;
  });
  await fixtures(page, async (route, url) => {
    if (url.searchParams.get("q") !== "slow") return false;
    await waiting;
    await route
      .fulfill({ json: { results: [], count: 0, page: 1, has_next: false } })
      .catch(() => {});
    return true;
  });
  await page.goto("/catalogue");
  await expect(page.getByRole("article")).toHaveCount(12);
  await page.getByRole("searchbox").fill("slow");
  await page.getByRole("searchbox").press("Enter");
  await expect(page.getByRole("status")).toHaveText("Loading\u2026");
  await page.getByRole("button", { name: "Clear search" }).click();
  await expect(page.getByRole("article")).toHaveCount(12);
  release();
  await expect(page.getByRole("article")).toHaveCount(12);
});
