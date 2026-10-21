import { expect, test } from "@playwright/test";
import { mkdirSync } from "node:fs";
import { tmpdir } from "node:os";
import { basename, join } from "node:path";

test.use({ serviceWorkers: "block", viewport: { width: 320, height: 800 } });
const pathway = {
  id: 1,
  title: "Data Analyst",
  target_outcome: "Practice with data",
  description: "Offline fixture",
  locale: "KE",
};
const lesson = {
  id: 9,
  title: "Compare a small table",
  summary: "Explain an observation and a limitation.",
  url: "https://resource.example.test/table",
  source: "Fixture publisher",
  skills: ["SQL"],
  is_low_data: true,
  done: false,
  source_reuse_verified: false,
};
const checkpoint = {
  id: 11,
  title: "SQL checkpoint",
  skill: "SQL",
  criteria: "Write a query and explain the result.",
  quiz: [1, 2, 3].map((index) => ({
    question: `Question ${index}`,
    options: ["Check the evidence", "Guess"],
  })),
};
const dashboard = {
  pathway,
  progress_percent: 33,
  done: ["Spreadsheets"],
  remaining: ["SQL", "Statistics"],
  steps: [
    { skill: "Spreadsheets", checkpoint: "First checkpoint", status: "done" },
    { skill: "SQL", checkpoint: checkpoint.title, status: "remaining" },
    { skill: "Statistics", checkpoint: "Last checkpoint", status: "skipped" },
  ],
  next_checkpoint: checkpoint,
  items: [lesson],
};
const next = {
  unlocked_skill: "SQL",
  unlocks_text: "Practice explaining a small query.",
  next_checkpoint: checkpoint,
  items: [lesson],
  opportunities: [
    {
      id: 1,
      title: "Data Intern (sample)",
      provider: "Fixture",
      location: "Remote",
      url: "https://opportunity.example.test",
      match_percent: 80,
    },
  ],
};

async function fixtures(page, override) {
  const writes = [];
  await page.route("**/api/**", async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    if (request.method() !== "GET")
      writes.push({ path, body: request.postDataJSON() });
    if (override && (await override(route, path))) return;
    const reads = {
      "/api/csrf/": { csrf_token: "offline-csrf-fixture" },
      "/api/me/": {
        id: 1,
        chosen_pathway: 1,
        display_name: "Fixture",
        preferred_language: "en",
        phone: "",
      },
      "/api/pathways/": [pathway],
      "/api/dashboard/": dashboard,
      "/api/items/": [lesson],
      "/api/next/": next,
    };
    if (request.method() === "GET" && path in reads)
      return route.fulfill({ json: reads[path] });
    if (
      request.method() === "POST" &&
      [
        "/api/me/",
        "/api/demo/",
        "/api/pathway/restart/",
        "/api/pathway/skip/",
        "/api/pathway/switch/",
        "/api/items/9/done/",
        "/api/checkpoints/11/complete/",
        "/api/checkpoints/11/skip/",
      ].includes(path)
    )
      return route.fulfill({ json: {} });
    return route.abort();
  });
  return writes;
}
async function screenshot(page, name) {
  const directory = join(
    tmpdir(),
    `somai-u3-visual-${basename(process.env.SOMAI_E2E_DB_DIR)}`,
  );
  mkdirSync(directory, { recursive: true });
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path: join(directory, name), fullPage: true });
  console.log(`U3_VISUAL_DIRECTORY=${directory}`);
}
async function noOverflow(page) {
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth),
  ).toBeLessThanOrEqual(320);
}
async function answer(page) {
  for (let index = 0; index < 3; index++)
    await page
      .locator("fieldset")
      .nth(index)
      .getByRole("radio")
      .first()
      .check();
  await page.getByRole("checkbox").check();
}

test("mobile pathway shows ordered status and a working confirmed lesson action", async ({
  page,
}) => {
  const writes = await fixtures(page);
  await page.goto("/pathway");
  const steps = page.getByRole("list");
  await expect(steps.getByRole("listitem")).toHaveCount(3);
  await expect(steps.getByRole("listitem").nth(0)).toContainText("Completed");
  await expect(steps.locator('[aria-current="step"]')).toContainText("SQL");
  await expect(steps.getByRole("listitem").nth(2)).toContainText("Skipped");
  await noOverflow(page);
  await screenshot(page, "pathway-320.png");
  await page.getByRole("button", { name: "Mark lesson done" }).click();
  await expect(
    page.getByRole("button", { name: "Mark lesson done" }),
  ).toHaveCount(0);
  expect(
    writes.filter((write) => write.path === "/api/items/9/done/"),
  ).toHaveLength(1);
});

test("lesson write failures remain visible without optimistic completion or replay", async ({
  page,
}) => {
  const writes = await fixtures(page, async (route, path) => {
    if (path !== "/api/items/9/done/") return false;
    await route.fulfill({ status: 503, json: {} });
    return true;
  });
  await page.goto("/items");
  await page.getByRole("button", { name: "Mark lesson done" }).click();
  await expect(page.getByRole("alert")).toContainText("could not be confirmed");
  await expect(
    page.getByRole("button", { name: "Mark lesson done" }),
  ).toBeEnabled();
  expect(writes).toHaveLength(1);
});

test("checkpoint pending locks controls and submits the selected answers once", async ({
  page,
}) => {
  let release;
  const waiting = new Promise((resolve) => {
    release = resolve;
  });
  const writes = await fixtures(page, async (route, path) => {
    if (path !== "/api/checkpoints/11/complete/") return false;
    await waiting;
    await route.fulfill({ json: {} });
    return true;
  });
  await page.goto("/checkpoint/11");
  await answer(page);
  await screenshot(page, "checkpoint-320.png");
  const complete = page.getByRole("button", {
    name: "Complete checkpoint",
    exact: true,
  });
  await complete.focus();
  await complete.press("Enter");
  await expect(complete).toBeDisabled();
  await expect(
    page.getByRole("button", { name: "Skip this checkpoint" }),
  ).toBeDisabled();
  await expect(page.getByRole("radio").first()).toBeDisabled();
  // Wait for the request to reach the network before the repeat activation
  // is attempted, so the assertion cannot race the dispatch.
  await expect.poll(() => writes.length).toBe(1);
  await page.keyboard.press("Enter");
  await page.waitForTimeout(500);
  expect(writes).toEqual([
    {
      path: "/api/checkpoints/11/complete/",
      body: { self_attested: true, quiz_answers: [0, 0, 0] },
    },
  ]);
  release();
  await expect(page).toHaveURL(/\/next$/);
  await expect(
    page.getByRole("heading", { name: "Data Intern (sample)" }),
  ).toBeVisible();
  await noOverflow(page);
  await screenshot(page, "next-320.png");
  await page.getByRole("button", { name: "Mark lesson done" }).click();
  await expect(
    page.getByRole("button", { name: "Mark lesson done" }),
  ).toHaveCount(0);
});

test("checkpoint failure keeps answers and attestation for inspection", async ({
  page,
}) => {
  const writes = await fixtures(page, async (route, path) => {
    if (path !== "/api/checkpoints/11/complete/") return false;
    await route.fulfill({ status: 503, json: {} });
    return true;
  });
  await page.goto("/checkpoint/11");
  await answer(page);
  await page
    .getByRole("button", { name: "Complete checkpoint", exact: true })
    .click();
  await expect(page.getByRole("alert")).toBeVisible();
  await expect(page.getByRole("checkbox")).toBeChecked();
  await expect(page.getByRole("radio").first()).toBeChecked();
  await expect(page).toHaveURL(/checkpoint\/11/);
  expect(writes).toHaveLength(1);
});

test("restart requires confirmation and switch or skip write only their existing endpoint", async ({
  page,
}) => {
  const writes = await fixtures(page, async (route, path) => {
    if (path !== "/api/pathways/") return false;
    await route.fulfill({
      json: [pathway, { ...pathway, id: 2, title: "Another topic" }],
    });
    return true;
  });
  await page.goto("/pathway");
  page.once("dialog", (dialog) => dialog.dismiss());
  await page.getByRole("button", { name: "Restart this pathway" }).click();
  expect(writes).toHaveLength(0);
  page.once("dialog", (dialog) => dialog.accept());
  await page.getByRole("button", { name: "Restart this pathway" }).click();
  await expect.poll(() => writes.length).toBe(1);
  await expect(
    page.getByRole("button", { name: "Skip this checkpoint" }),
  ).toBeEnabled();
  await page.getByRole("button", { name: "Skip this checkpoint" }).click();
  await expect.poll(() => writes.length).toBe(2);
  await expect(
    page.getByRole("combobox", { name: "Switch pathway" }),
  ).toBeEnabled();
  await page
    .getByRole("combobox", { name: "Switch pathway" })
    .selectOption("2");
  await expect.poll(() => writes.length).toBe(3);
  expect(writes[2].body).toEqual({ pathway_id: "2" });
  expect(writes.map((write) => write.path)).toEqual([
    "/api/pathway/restart/",
    "/api/pathway/skip/",
    "/api/pathway/switch/",
  ]);
});

test("failed reads distinguish errors from guest and empty states and allow explicit retry", async ({
  page,
}) => {
  let failed = true;
  const writes = await fixtures(page, async (route, path) => {
    if (!["/api/dashboard/", "/api/next/"].includes(path)) return false;
    await route.fulfill({
      status: failed ? 503 : 200,
      json: failed
        ? {}
        : path === "/api/next/"
          ? { available: false, reason: "no_checkpoint" }
          : dashboard,
    });
    return true;
  });
  await page.goto("/pathway");
  await expect(page.getByRole("alert")).toContainText("could not be loaded");
  await expect(page.getByText("Choose a pathway to get started.")).toHaveCount(
    0,
  );
  failed = false;
  await page.getByRole("button", { name: "Retry" }).click();
  await expect(
    page.getByRole("heading", { name: "Data Analyst", exact: true }),
  ).toBeVisible();
  failed = true;
  await page.goto("/next");
  await expect(page.getByRole("alert")).toBeVisible();
  failed = false;
  await page.getByRole("button", { name: "Retry" }).click();
  await expect(
    page.getByText("Complete a checkpoint to see your next steps."),
  ).toBeVisible();
  expect(writes).toHaveLength(0);
});

test("onboarding pending and errors are explicit while name stays optional", async ({
  page,
}) => {
  const writes = await fixtures(page, async (route, path) => {
    if (path !== "/api/me/" || route.request().method() !== "POST")
      return false;
    await route.fulfill({ status: 503, json: {} });
    return true;
  });
  await page.goto("/");
  await page
    .getByRole("combobox", { name: "Learning pathway", exact: true })
    .selectOption("1");
  await page
    .getByRole("button", { name: "Start learning", exact: true })
    .click();
  await expect(page.getByRole("alert")).toBeVisible();
  expect(writes[0].body.display_name).toBe("Learner");
  await noOverflow(page);
  await screenshot(page, "onboarding-error-320.png");
});

test("empty reading lists and completed pathways explain the next choices", async ({
  page,
}) => {
  await fixtures(page, async (route, path) => {
    if (path === "/api/items/") {
      await route.fulfill({ json: [] });
      return true;
    }
    if (path === "/api/dashboard/") {
      await route.fulfill({
        json: { ...dashboard, items: [], next_checkpoint: null, remaining: [] },
      });
      return true;
    }
    return false;
  });
  await page.goto("/items");
  await expect(page.getByText(/No reading picks/)).toBeVisible();
  await page.goto("/pathway");
  await expect(page.getByText(/reached the end/)).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Skip this checkpoint" }),
  ).toBeDisabled();
  await noOverflow(page);
});

test("unavailable checkpoints do not render another checkpoint and new English text has language marking", async ({
  page,
}) => {
  await fixtures(page);
  await page.addInitScript(() => localStorage.setItem("somai-language", "sw"));
  await page.goto("/checkpoint/999");
  const unavailable = page.getByText(
    "This checkpoint is not available on the current pathway.",
  );
  await expect(unavailable).toHaveAttribute("lang", "en");
  await expect(page.getByRole("radio")).toHaveCount(0);
  await page.goto("/pathway");
  await expect(
    page.getByRole("heading", { name: "Your learning steps" }).locator(".."),
  ).toHaveAttribute("lang", "en");
});

test("onboarding blocks duplicate writes and demo while a start request is pending", async ({
  page,
}) => {
  let release;
  const waiting = new Promise((resolve) => {
    release = resolve;
  });
  const writes = await fixtures(page, async (route, path) => {
    if (path !== "/api/me/" || route.request().method() !== "POST")
      return false;
    await waiting;
    await route.fulfill({ status: 503, json: {} });
    return true;
  });
  await page.goto("/");
  await page
    .getByRole("combobox", { name: "Learning pathway", exact: true })
    .selectOption("1");
  const start = page.getByRole("button", {
    name: "Start learning",
    exact: true,
  });
  await start.press("Enter");
  await expect(start).toBeDisabled();
  await expect(
    page.getByRole("button", { name: "Open the demo learner" }),
  ).toBeDisabled();
  // Wait for the request to reach the network before the repeat activation
  // and the count assertion, so the check cannot race the dispatch.
  await expect.poll(() => writes.length).toBe(1);
  await page.keyboard.press("Enter");
  await page.waitForTimeout(500);
  expect(writes).toHaveLength(1);
  release();
  await expect(page.getByRole("alert")).toBeVisible();
});

test("lesson pending state waits for confirmation and locks repeated activation", async ({
  page,
}) => {
  let release;
  const waiting = new Promise((resolve) => {
    release = resolve;
  });
  const writes = await fixtures(page, async (route, path) => {
    if (path !== "/api/items/9/done/") return false;
    await waiting;
    await route.fulfill({ json: {} });
    return true;
  });
  await page.goto("/items");
  const button = page.getByRole("button", { name: "Mark lesson done" });
  await button.press("Enter");
  await expect(button).toBeDisabled();
  // The request must reach the network before the repeat activation is
  // attempted. Asserting the write count without waiting for it races the
  // dispatch and fails on a slower machine.
  await expect.poll(() => writes.length).toBe(1);
  await page.keyboard.press("Enter");
  await page.waitForTimeout(500);
  expect(writes).toHaveLength(1);
  release();
  await expect(button).toHaveCount(0);
});

test("checkpoint route changes reset answers and skip navigates only after confirmation", async ({
  page,
}) => {
  let second = false;
  let release;
  const waiting = new Promise((resolve) => {
    release = resolve;
  });
  const writes = await fixtures(page, async (route, path) => {
    if (path === "/api/dashboard/" && second) {
      await route.fulfill({
        json: {
          ...dashboard,
          next_checkpoint: {
            ...checkpoint,
            id: 12,
            title: "Second checkpoint",
          },
        },
      });
      return true;
    }
    if (path === "/api/checkpoints/12/skip/") {
      await waiting;
      await route.fulfill({ json: {} });
      return true;
    }
    return false;
  });
  await page.goto("/checkpoint/11");
  await answer(page);
  second = true;
  await page.evaluate(() => {
    history.pushState({}, "", "/checkpoint/12");
    dispatchEvent(new PopStateEvent("popstate"));
  });
  await expect(
    page.getByRole("heading", { name: "Second checkpoint" }),
  ).toBeVisible();
  await expect(page.getByRole("checkbox")).not.toBeChecked();
  await expect(page.getByRole("radio").first()).not.toBeChecked();
  await expect(
    page.getByRole("button", { name: "Complete checkpoint", exact: true }),
  ).toBeDisabled();
  await page.getByRole("button", { name: "Skip this checkpoint" }).click();
  await expect(
    page.getByRole("button", { name: "Skip this checkpoint" }),
  ).toBeDisabled();
  await expect(page).toHaveURL(/checkpoint\/12/);
  // Wait for the skip request to reach the network before asserting, so the
  // check cannot race the dispatch on a slower machine.
  await expect.poll(() => writes.length).toBe(1);
  expect(writes).toHaveLength(1);
  release();
  await expect(page).toHaveURL(/\/pathway$/);
});
