import { expect, test } from "@playwright/test";

test.use({ serviceWorkers: "block" });
const token = "a".repeat(64);
const password = "Synthetic-new-otter-728!";

async function fixtures(
  page,
  { available = true, authenticated = false, verified = false, override } = {},
) {
  const writes = [];
  await page.route("**/api/**", async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    if (request.method() !== "GET")
      writes.push({ path, body: request.postDataJSON() });
    if (override && (await override(route, path))) return;
    const reads = {
      "/api/me/": null,
      "/api/pathways/": [],
      "/api/csrf/": { csrf_token: "offline-csrf-fixture" },
      "/api/account/": {
        authenticated,
        email: "owner@example.test",
        email_verified: verified,
      },
      "/api/account/recovery/options/": {
        available,
        mode: available ? "memory" : "disabled",
        live_delivery: false,
      },
    };
    if (request.method() === "GET" && path in reads) {
      return route.fulfill({
        status: path === "/api/me/" ? 401 : 200,
        json: reads[path],
      });
    }
    if (
      request.method() === "POST" &&
      /\/account\/(verify|reset)\/(request|confirm)\/$/.test(path)
    )
      return route.fulfill({
        status: path.endsWith("request/") ? 202 : 200,
        json: { confirmed: true },
      });
    return route.abort();
  });
  return writes;
}

test("disabled delivery stays unavailable and fragment is scrubbed without a write", async ({
  page,
}) => {
  const writes = await fixtures(page, { available: false });
  await page.goto(`/account/reset#token=${token}`);
  await expect(page).toHaveURL(/\/account\/reset$/);
  await expect(
    page.getByText("Email delivery is disabled.", { exact: false }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Confirm password reset" }),
  ).toHaveCount(0);
  expect(writes).toEqual([]);
  await page.goto("/account");
  await expect(
    page.getByRole("button", { name: "Sign in", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Continue learning" }),
  ).toBeVisible();
});

test("verification requires an explicit confirmation and never displays the token", async ({
  page,
}) => {
  const writes = await fixtures(page);
  await page.goto(`/account/verify#token=${token}`);
  await expect(page).toHaveURL(/\/account\/verify$/);
  await expect(
    page.getByRole("button", { name: "Confirm email verification" }),
  ).toBeVisible();
  expect(writes).toEqual([]);
  await expect(page.locator("body")).not.toContainText(token);
  await page
    .getByRole("button", { name: "Confirm email verification" })
    .click();
  await expect(page.getByRole("status")).toHaveText(
    "Email verified. This does not sign you in.",
  );
  expect(writes).toEqual([
    { path: "/api/account/verify/confirm/", body: { token } },
  ]);
});

test("reset pending prevents duplicate writes and success requires explicit sign in", async ({
  page,
}) => {
  let finish;
  const writes = await fixtures(page, {
    override: async (route, path) => {
      if (path !== "/api/account/reset/confirm/") return false;
      await new Promise((resolve) => {
        finish = resolve;
      });
      await route.fulfill({ json: { confirmed: true } });
      return true;
    },
  });
  await page.goto(`/account/reset#token=${token}`);
  await page.getByLabel("New password").fill(password);
  const confirm = page.getByRole("button", { name: "Confirm password reset" });
  await confirm.click();
  await expect(confirm).toBeDisabled();
  await expect(page.getByLabel("New password")).toBeDisabled();
  expect(writes).toHaveLength(1);
  finish();
  await expect(page.getByRole("status")).toContainText(
    "Sign in explicitly with your new password.",
  );
  await expect(page.getByLabel("New password")).toHaveCount(0);
  expect(writes[0].body).toEqual({ token, password });
  expect(writes).toHaveLength(1);
});

test("expired or rejected confirmation gives an error without automatic replay", async ({
  page,
}) => {
  const writes = await fixtures(page, {
    override: async (route, path) => {
      if (path !== "/api/account/verify/confirm/") return false;
      await route.fulfill({ status: 400, json: { detail: "invalid" } });
      return true;
    },
  });
  await page.goto(`/account/verify#token=${token}`);
  const confirm = page.getByRole("button", {
    name: "Confirm email verification",
  });
  await confirm.click();
  await expect(page.getByRole("alert")).toContainText("not accepted");
  await expect(confirm).toBeEnabled();
  expect(writes).toHaveLength(1);
});

test("request previews disclose memory-only delivery and use generic recovery result", async ({
  page,
}) => {
  const writes = await fixtures(page);
  await page.goto("/account");
  await expect(
    page.getByText("Offline preview:", { exact: false }),
  ).toBeVisible();
  await page.getByLabel("Verified account email").fill("unknown@example.test");
  await page.getByRole("button", { name: "Create recovery preview" }).click();
  await expect(page.getByRole("status")).toContainText("If eligible");
  expect(writes).toEqual([
    {
      path: "/api/account/reset/request/",
      body: { email: "unknown@example.test" },
    },
  ]);
});

test("owner verification button respects verified status and request failures stay visible", async ({
  page,
}) => {
  const writes = await fixtures(page, {
    authenticated: true,
    override: async (route, path) => {
      if (path !== "/api/account/verify/request/") return false;
      await route.fulfill({ status: 503, json: {} });
      return true;
    },
  });
  await page.goto("/account");
  await page
    .getByRole("button", { name: "Create verification preview" })
    .click();
  await expect(page.getByRole("alert")).toContainText("No automatic retry");
  expect(writes).toHaveLength(1);
  await page.unrouteAll({ behavior: "wait" });
  await fixtures(page, { authenticated: true, verified: true });
  await page.reload();
  await expect(
    page.getByText("Email verified.", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Create verification preview" }),
  ).toBeDisabled();
});

test("capability load failure can retry and missing tokens cannot submit", async ({
  page,
}) => {
  let first = true;
  const writes = await fixtures(page, {
    override: async (route, path) => {
      if (path !== "/api/account/recovery/options/" || !first) return false;
      first = false;
      await route.fulfill({ status: 503, json: {} });
      return true;
    },
  });
  await page.goto("/account/reset");
  await expect(page.getByRole("alert")).toContainText(
    "Could not load recovery availability",
  );
  await page.getByRole("button", { name: "Retry", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("not accepted");
  await expect(
    page.getByRole("button", { name: "Confirm password reset" }),
  ).toHaveCount(0);
  expect(writes).toEqual([]);
});

test("mobile reset labels remain readable and English-marked", async ({
  page,
}) => {
  await page.setViewportSize({ width: 320, height: 800 });
  await page.addInitScript(() => localStorage.setItem("somai-language", "sw"));
  await fixtures(page);
  await page.goto(`/account/reset#token=${token}`);
  await expect(page.locator(".account-form")).toHaveAttribute("lang", "en");
  await page.getByLabel("New password").focus();
  await expect(page.getByLabel("New password")).toBeFocused();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: test.info().outputPath("recovery-mobile.png"),
    fullPage: true,
  });
});
