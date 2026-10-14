import { expect, test } from "@playwright/test";
import { resetE2ESeed } from "./reset-e2e-seed.js";
import { writeFileSync, unlinkSync } from "node:fs";

const password = "Synthetic-independent-otter-729!";
test.beforeEach(() => resetE2ESeed());

async function account(page) {
  await page.goto("/account");
  await expect(
    page.getByRole("button", { name: "Sign in", exact: true }),
  ).toBeVisible();
}

async function credentials(page) {
  await page.getByLabel("Email address").fill("learner@example.test");
  await page.getByLabel("Password", { exact: true }).fill(password);
}

test("optional account attaches guest progress and restores it after logout", async ({
  page,
}) => {
  await page.goto("/");
  const option = page
    .getByLabel("Learning pathway")
    .locator("option")
    .filter({ hasText: /^Data Analyst/ })
    .first();
  await page
    .getByLabel("Learning pathway")
    .selectOption(await option.getAttribute("value"));
  await page.getByRole("button", { name: "Start learning" }).click();
  await expect(
    page.getByRole("heading", { name: "Data Analyst", exact: true }),
  ).toBeVisible();
  const before = await (await page.request.get("/api/me/")).json();
  await account(page);
  await credentials(page);
  await page.getByRole("checkbox", { name: /Attach this guest/ }).check();
  await page
    .getByRole("button", { name: "Create account", exact: true })
    .click();
  await expect(page).toHaveURL(/\/pathway$/);
  const after = await (await page.request.get("/api/me/")).json();
  expect(after.id).toBe(before.id);
  await page.goto("/account");
  await expect(page.getByText("Signed in as:", { exact: false })).toBeVisible();
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Sign in", exact: true }),
  ).toBeVisible();
  expect((await page.request.get("/api/me/")).status()).toBe(401);
  await credentials(page);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page).toHaveURL(/\/pathway$/);
  expect((await (await page.request.get("/api/me/")).json()).id).toBe(
    before.id,
  );
});

test("account deletion requires password and leaves a new guest journey available", async ({
  page,
}) => {
  await account(page);
  await credentials(page);
  await page
    .getByRole("button", { name: "Create account", exact: true })
    .click();
  await expect(page).toHaveURL(/\/pathway$/);
  await page.goto("/account");
  await expect(
    page.getByRole("button", { name: "Sign out", exact: true }),
  ).toBeVisible();
  page.on("dialog", (dialog) => dialog.accept());
  await page.getByLabel("Password", { exact: true }).fill("incorrect");
  await page
    .getByRole("button", { name: "Delete account and progress" })
    .click();
  await expect(page.getByRole("alert")).toHaveText(
    "Password confirmation failed.",
  );
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page
    .getByRole("button", { name: "Delete account and progress" })
    .click();
  await expect(
    page.getByRole("button", { name: "Sign in", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("link", { name: "Continue learning", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Start learning" }),
  ).toBeVisible();
});

test("missing CSRF and an untrusted origin cannot start a guest or login", async ({
  page,
}) => {
  expect((await page.request.post("/api/me/", { data: {} })).status()).toBe(
    403,
  );
  const csrf = await (await page.request.get("/api/csrf/")).json();
  const response = await page.request.post("/api/account/login/", {
    data: { email: "learner@example.test", password },
    headers: { "X-CSRFToken": csrf.csrf_token, Origin: "https://evil.example" },
  });
  expect(response.status()).toBe(403);
});

test("failed registration is visible and writes are not automatically retried", async ({
  page,
}) => {
  await account(page);
  let writes = 0;
  await page.route("**/api/account/", async (route) => {
    if (route.request().method() !== "POST") return route.continue();
    writes += 1;
    await route.fulfill({
      status: 503,
      json: { detail: "Offline account fixture" },
    });
  });
  await credentials(page);
  await page
    .getByRole("button", { name: "Create account", exact: true })
    .click();
  await expect(page.getByRole("alert")).toHaveText("Offline account fixture");
  expect(writes).toBe(1);
  await expect(
    page.getByRole("button", { name: "Create account", exact: true }),
  ).toBeEnabled();
});

test("mobile account controls fit and experimental interface marks English labels", async ({
  page,
}) => {
  await page.setViewportSize({ width: 320, height: 800 });
  await page.addInitScript(() => localStorage.setItem("somai-language", "sw"));
  await account(page);
  await expect(page.locator(".account-form")).toHaveAttribute("lang", "en");
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.getByLabel("Email address").focus();
  await expect(page.getByLabel("Email address")).toBeFocused();
  await page.screenshot({
    path: test.info().outputPath("account-mobile.png"),
    fullPage: true,
  });
});

test("new offline worker purges private legacy caches and never caches API data", async ({
  page,
}) => {
  // Seed before the application can install/activate its new worker.
  await page.goto("/manifest.webmanifest");
  await page.evaluate(async () => {
    const old = await caches.open("somai-shell-v1");
    await old.put("/api/dashboard/", new Response("private legacy fixture"));
    await navigator.serviceWorker.register("/sw.js");
    await navigator.serviceWorker.ready;
  });
  await page.reload();
  await expect
    .poll(() =>
      page.evaluate(() => Boolean(navigator.serviceWorker.controller)),
    )
    .toBe(true);
  await expect
    .poll(() =>
      page.evaluate(async () =>
        (await caches.keys()).includes("somai-shell-v1"),
      ),
    )
    .toBe(false);
  await account(page);
  await credentials(page);
  await page
    .getByRole("button", { name: "Create account", exact: true })
    .click();
  await expect(page).toHaveURL(/\/pathway$/);
  const privateKeys = await page.evaluate(async () => {
    const found = [];
    for (const name of await caches.keys()) {
      for (const request of await (await caches.open(name)).keys()) {
        if (new URL(request.url).pathname.startsWith("/api/"))
          found.push(request.url);
      }
    }
    return found;
  });
  expect(privateKeys).toEqual([]);
});

test("legacy controlling worker blocks account requests until updated", async ({
  page,
}) => {
  // Worker script fetches bypass page routing: serve an explicit offline fixture.
  const fixture = new URL("../dist/p3-legacy-worker.js", import.meta.url);
  writeFileSync(
    fixture,
    "self.addEventListener('install',e=>e.waitUntil(self.skipWaiting()));self.addEventListener('activate',e=>e.waitUntil(self.clients.claim()));",
  );
  try {
    await page.addInitScript(() => {
      const original = navigator.serviceWorker.register.bind(
        navigator.serviceWorker,
      );
      navigator.serviceWorker.register = (url, options) =>
        url === "/sw.js"
          ? navigator.serviceWorker.getRegistration()
          : original(url, options);
    });
    await page.goto("/manifest.webmanifest");
    await page.evaluate(async () => {
      await navigator.serviceWorker.register("/p3-legacy-worker.js");
      await navigator.serviceWorker.ready;
    });
    await expect
      .poll(() =>
        page.evaluate(() => Boolean(navigator.serviceWorker.controller)),
      )
      .toBe(true);
    let requests = 0;
    page.on("request", (request) => {
      if (new URL(request.url()).pathname === "/api/account/") requests += 1;
    });
    await page.goto("/account");
    await expect(page.getByRole("alert")).toContainText(
      "Could not load account status",
    );
    expect(requests).toBe(0);
  } finally {
    unlinkSync(fixture);
  }
});
