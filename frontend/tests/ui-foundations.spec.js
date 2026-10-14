import { expect, test } from "@playwright/test";
import { mkdirSync } from "node:fs";
import { tmpdir } from "node:os";
import { basename, join } from "node:path";

test.use({ serviceWorkers: "block" });

const pathway = {
  id: 1,
  title: "Data Analyst",
  description: "Offline interface fixture.",
  target_outcome: "Junior Data Analyst",
  locale: "KE",
};
const lesson = {
  id: 1,
  title: "Practice reading a small table",
  url: "https://resource.example.test/table",
  summary: "Compare two values and explain one limitation of the table.",
  source: "Offline fixture publisher",
  source_attribution: "Fixture author",
  source_url: "https://resource.example.test/feed",
  source_rights: "not stated",
  content_date: "2026-10-01",
  date_source: "published",
  fetched_at: "2026-10-13T09:00:00Z",
  skills: ["Spreadsheets"],
  is_low_data: true,
  done: false,
};
const checkpoint = {
  id: 11,
  title: "Spreadsheets checkpoint",
  skill: "Spreadsheets",
  criteria: "Create a five-row budget and explain how the total changes.",
  quiz: ["Check a total", "Compare two rows", "Explain a limitation"].map(
    (question) => ({
      question,
      options: ["Check the evidence", "Guess the result"],
    }),
  ),
};

test.beforeEach(async ({ page }) => {
  await page.route("**/api/**", (route) => {
    const path = new URL(route.request().url()).pathname;
    const responses = {
      "/api/me/": {
        id: 1,
        display_name: "Interface fixture",
        preferred_language: "en",
        chosen_pathway: 1,
        reminder_opt_in: false,
        phone: "",
      },
      "/api/pathways/": [pathway],
      "/api/dashboard/": {
        pathway,
        progress_percent: 33,
        done: ["SQL"],
        remaining: ["Spreadsheets", "Statistics"],
        next_checkpoint: checkpoint,
        items: [lesson],
      },
      "/api/items/": [lesson],
    };
    if (route.request().method() !== "GET" || !(path in responses)) {
      return route.abort();
    }
    return route.fulfill({ json: responses[path] });
  });
});

function rgb(value) {
  if (value.startsWith("#")) {
    return value
      .slice(1)
      .match(/.{2}/g)
      .map((part) => parseInt(part, 16) / 255);
  }
  return value
    .match(/[\d.]+/g)
    .slice(0, 3)
    .map((part) => Number(part) / 255);
}
function contrast(foreground, background) {
  const luminance = (value) =>
    rgb(value)
      .map((channel) =>
        channel <= 0.04045
          ? channel / 12.92
          : ((channel + 0.055) / 1.055) ** 2.4,
      )
      .reduce(
        (total, channel, index) =>
          total + channel * [0.2126, 0.7152, 0.0722][index],
        0,
      );
  const values = [luminance(foreground), luminance(background)].sort(
    (a, b) => b - a,
  );
  return (values[0] + 0.05) / (values[1] + 0.05);
}
async function colors(locator) {
  return locator.evaluate((element) => {
    const style = getComputedStyle(element);
    return { foreground: style.color, background: style.backgroundColor };
  });
}
async function settleMotion(locator) {
  await locator.evaluate((element) =>
    Promise.all(element.getAnimations().map((animation) => animation.finished)),
  );
}
async function noHorizontalOverflow(page) {
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth),
  ).toBeLessThanOrEqual(await page.evaluate(() => window.innerWidth));
}
async function screenshot(page, name) {
  const directory = join(
    tmpdir(),
    "somai-u1-visual-" + basename(process.env.SOMAI_E2E_DB_DIR),
  );
  mkdirSync(directory, { recursive: true });
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path: join(directory, name), fullPage: true });
  console.log("U1_VISUAL_DIRECTORY=" + directory);
}

test("keyboard skip link bypasses navigation and continues into native form controls", async ({
  page,
}) => {
  await page.goto("/");
  const skip = page.getByRole("link", { name: "Skip to main content" });
  const hiddenBox = await skip.boundingBox();
  expect(hiddenBox.y + hiddenBox.height).toBeLessThanOrEqual(0);
  await page.keyboard.press("Tab");
  await expect(skip).toBeFocused();
  expect((await skip.boundingBox()).y).toBeGreaterThanOrEqual(0);
  const focus = await skip.evaluate((element) => {
    const style = getComputedStyle(element);
    return {
      width: parseFloat(style.outlineWidth),
      color: style.outlineColor,
      adjacent: getComputedStyle(document.documentElement).backgroundColor,
    };
  });
  expect(focus.width).toBeGreaterThanOrEqual(2);
  expect(contrast(focus.color, focus.adjacent)).toBeGreaterThanOrEqual(3);
  await page.keyboard.press("Enter");
  await expect(page.locator("#main-content")).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(
    page.getByRole("combobox", { name: "Language", exact: true }),
  ).toBeFocused();
});

test("current-page navigation follows routes without changing link destinations", async ({
  page,
}) => {
  await page.goto("/pathway");
  const navigation = page.getByRole("navigation", { name: "Main navigation" });
  await expect(navigation.locator('[aria-current="page"]')).toHaveText(
    "Your pathway",
  );
  await navigation
    .getByRole("link", { name: "Lessons for your pathway" })
    .click();
  await expect(navigation.locator('[aria-current="page"]')).toHaveText(
    "Lessons for your pathway",
  );
  await expect(
    navigation.getByRole("link", { name: "Your pathway", exact: true }),
  ).toHaveAttribute("href", "/pathway");
  await navigation.getByRole("link", { name: "Settings" }).click();
  await expect(navigation.locator('[aria-current="page"]')).toHaveText(
    "Settings",
  );
  await expect(navigation.locator('[aria-current="page"]')).toHaveCount(1);
});

test("native selects and disabled buttons retain browser behavior", async ({
  page,
}) => {
  await page.goto("/");
  const pathwaySelect = page.getByRole("combobox", {
    name: "Learning pathway",
    exact: true,
  });
  const start = page.getByRole("button", {
    name: "Start learning",
    exact: true,
  });
  await expect(start).toBeDisabled();
  expect(
    await pathwaySelect.evaluate(
      (element) => element instanceof HTMLSelectElement && element.required,
    ),
  ).toBe(true);
  expect(
    await start.evaluate((element) => element instanceof HTMLButtonElement),
  ).toBe(true);
  await pathwaySelect.selectOption("1");
  await expect(start).toBeEnabled();
  await pathwaySelect.focus();
  await page.keyboard.press("Tab");
  await expect(page.getByLabel("Name (optional)")).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(start).toBeFocused();
});

test("native radio groups checkbox and disclosure remain keyboard operable", async ({
  page,
}) => {
  await page.goto("/checkpoint/11");
  const radios = page.getByRole("radio");
  await expect(radios).toHaveCount(6);
  await radios.first().focus();
  await page.keyboard.press("Space");
  await expect(radios.first()).toBeChecked();
  await page.keyboard.press("ArrowDown");
  await expect(radios.nth(1)).toBeChecked();
  await expect(radios.first()).not.toBeChecked();
  const checkbox = page.getByRole("checkbox");
  await checkbox.focus();
  await page.keyboard.press("Space");
  await expect(checkbox).toBeChecked();
  await expect(
    page.getByRole("button", { name: "Complete checkpoint", exact: true }),
  ).toBeDisabled();
  await page.goto("/items");
  const summary = page.locator(".item-provenance summary");
  await summary.focus();
  await page.keyboard.press("Enter");
  await expect(page.locator("details")).toHaveAttribute("open", "");
  await page.keyboard.press("Space");
  await expect(page.locator("details")).not.toHaveAttribute("open", "");
});

test("token palette and rendered action states retain readable contrast", async ({
  page,
}) => {
  await page.goto("/");
  const palette = await page.evaluate(() => {
    const style = getComputedStyle(document.documentElement);
    const read = (name) => style.getPropertyValue("--color-" + name).trim();
    return [
      [read("text"), read("page")],
      [read("text"), read("surface")],
      [read("muted"), read("page")],
      [read("muted"), read("surface")],
      [read("text"), read("callout")],
      [read("text"), read("notice")],
      [read("disabled-text"), read("disabled")],
    ];
  });
  for (const [foreground, background] of palette) {
    expect(contrast(foreground, background)).toBeGreaterThanOrEqual(4.5);
  }
  const field = page.getByLabel("Name (optional)");
  const border = await field.evaluate((element) => {
    const style = getComputedStyle(element);
    return {
      foreground: style.borderTopColor,
      background: style.backgroundColor,
    };
  });
  expect(contrast(border.foreground, border.background)).toBeGreaterThanOrEqual(
    3,
  );
  await page
    .getByRole("combobox", { name: "Learning pathway", exact: true })
    .selectOption("1");
  for (const button of [
    page.getByRole("button", { name: "Start learning", exact: true }),
    page.getByRole("button", { name: "Open the demo learner" }),
  ]) {
    await settleMotion(button);
    const normal = await colors(button);
    expect(
      contrast(normal.foreground, normal.background),
    ).toBeGreaterThanOrEqual(4.5);
    await button.hover();
    await settleMotion(button);
    await expect
      .poll(async () => {
        const hover = await colors(button);
        return contrast(hover.foreground, hover.background);
      })
      .toBeGreaterThanOrEqual(4.5);
  }
  await page.goto("/settings");
  const danger = page.getByRole("button", { name: "Delete my data" });
  await danger.hover();
  await settleMotion(danger);
  const dangerColors = await colors(danger);
  expect(
    contrast(dangerColors.foreground, dangerColors.background),
  ).toBeGreaterThanOrEqual(4.5);
});

test("320px layouts keep native controls and major touch targets usable", async ({
  page,
}) => {
  await page.setViewportSize({ width: 320, height: 800 });
  for (const path of [
    "/",
    "/pathway",
    "/items",
    "/settings",
    "/checkpoint/11",
  ]) {
    await page.goto(path);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    await noHorizontalOverflow(page);
    const controls = page.locator(
      'button, select, input:not([type="radio"]):not([type="checkbox"]), .site-header a, .radio, summary',
    );
    for (const control of await controls.all()) {
      const box = await control.boundingBox();
      expect(box.height).toBeGreaterThanOrEqual(44);
      expect(box.width).toBeGreaterThanOrEqual(44);
    }
  }
  await screenshot(page, "checkpoint-320.png");
});

test("200 percent text resizing preserves settings reflow and controls", async ({
  page,
}) => {
  await page.setViewportSize({ width: 640, height: 900 });
  await page.goto("/settings");
  await page.evaluate(() => {
    document.documentElement.style.fontSize = "200%";
  });
  await noHorizontalOverflow(page);
  const phone = page.getByLabel("Phone (optional)");
  expect(
    await phone.evaluate((element) =>
      parseFloat(getComputedStyle(element).fontSize),
    ),
  ).toBeGreaterThanOrEqual(32);
  await phone.fill("0700000000");
  await expect(phone).toHaveValue("0700000000");
  await screenshot(page, "settings-text-200.png");
});

test("reduced motion suppresses control transitions and scrolling animation", async ({
  page,
}) => {
  await page.emulateMedia({ reducedMotion: "no-preference" });
  await page.goto("/");
  const demo = page.getByRole("button", { name: "Open the demo learner" });
  await demo.hover();
  expect(
    await demo.evaluate(
      (element) => getComputedStyle(element).transitionDuration,
    ),
  ).not.toBe("0s");
  await page.emulateMedia({ reducedMotion: "reduce" });
  const styles = await page
    .getByRole("button", { name: "Open the demo learner" })
    .evaluate((element) => {
      const style = getComputedStyle(element);
      return {
        duration: style.transitionDuration,
        animation: style.animationName,
        scrolling: style.scrollBehavior,
      };
    });
  expect(styles).toEqual({
    duration: "0s",
    animation: "none",
    scrolling: "auto",
  });
  await page.setViewportSize({ width: 1440, height: 900 });
  await screenshot(page, "onboarding-desktop.png");
});

test("forced colors preserve visible focus native controls and current-page cues", async ({
  page,
}) => {
  await page.emulateMedia({ forcedColors: "active" });
  await page.setViewportSize({ width: 320, height: 800 });
  await page.goto("/settings");
  const skip = page.getByRole("link", { name: "Skip to main content" });
  await expect(skip).toHaveAttribute("href", "#main-content");
  await page.keyboard.press("Tab");
  await expect(skip).toBeFocused();
  expect(
    await skip.evaluate((element) => getComputedStyle(element).outlineStyle),
  ).toBe("solid");
  await page.keyboard.press("Enter");
  await page.keyboard.press("Tab");
  const language = page.getByRole("combobox", {
    name: "Language",
    exact: true,
  });
  await expect(language).toBeFocused();
  expect(
    await language.evaluate((element) => getComputedStyle(element).appearance),
  ).toBe("auto");
  await expect(page.locator('nav [aria-current="page"]')).toHaveText(
    "Settings",
  );
  await noHorizontalOverflow(page);
  await screenshot(page, "settings-forced-colors.png");
});

test("English skip text is language-marked in the experimental Kiswahili interface", async ({
  page,
}) => {
  await page.goto("/");
  await page
    .getByRole("combobox", { name: "Language", exact: true })
    .selectOption("sw");
  await expect(page.locator("html")).toHaveAttribute("lang", "sw");
  await expect(
    page.getByRole("link", { name: "Skip to main content" }),
  ).toHaveAttribute("lang", "en");
});
