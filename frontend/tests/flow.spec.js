import { test, expect } from "@playwright/test";

test("onboard and complete a checkpoint in English and Swahili", async ({
  page,
}) => {
  for (const flow of [
    {
      language: "English",
      pathwayLabel: "Learning pathway",
      pathway: /Data Analyst/,
      start: "Start learning",
      dashboard: "Data Analyst",
      open: "Open checkpoint",
      attest: "I completed the practice and meet these criteria.",
      complete: "Complete checkpoint",
      next: "What’s next",
      opportunities: "Related opportunities (sample listings)",
    },
    {
      language: "Kiswahili",
      pathwayLabel: "Njia ya kujifunza",
      pathway: /Mchambuzi wa Data/,
      start: "Anza kujifunza",
      dashboard: "Mchambuzi wa Data",
      open: "Fungua hatua",
      attest: "Nimefanya mazoezi na kutimiza vigezo hivi.",
      complete: "Kamilisha hatua",
      next: "Hatua inayofuata",
      opportunities: "Fursa zinazohusiana (mifano)",
    },
  ]) {
    await page.goto("/");
    if (flow.language === "Kiswahili")
      await page.getByLabel("Language").selectOption("sw");
    const pathwaySelect = page.getByLabel(flow.pathwayLabel);
    const pathwayOption = pathwaySelect
      .locator("option")
      .filter({ hasText: flow.pathway })
      .first();
    await pathwaySelect.selectOption(await pathwayOption.getAttribute("value"));
    await page.getByRole("button", { name: flow.start }).click();
    await expect(
      page.getByRole("heading", { name: flow.dashboard }),
    ).toBeVisible();
    await page.getByRole("button", { name: flow.open }).click();
    for (let i = 0; i < 3; i += 1)
      await page.locator("fieldset").nth(i).getByRole("radio").first().check();
    await page.getByRole("checkbox", { name: flow.attest }).check();
    await page.getByRole("button", { name: flow.complete }).click();
    await expect(page.getByRole("heading", { name: flow.next })).toBeVisible();
    await expect(page.getByText(flow.opportunities)).toBeVisible();
  }
});

test("direct /next load shows matched sample opportunities", async ({
  page,
}) => {
  await page.addInitScript(() => sessionStorage.clear());
  const response = await page.request.post("/api/demo/");
  expect(response.ok()).toBeTruthy();

  await page.goto("/next");

  await expect(
    page.getByRole("heading", { name: "What’s next" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Data Intern (sample)" }),
  ).toBeVisible();
  await expect(page.getByText("Sample listing").first()).toBeVisible();
});

test("/next explains when no learner exists in both languages", async ({
  page,
}) => {
  for (const language of [
    {
      code: "en",
      message:
        "Choose a pathway first to see your next steps and matched opportunities.",
      link: "Choose a pathway",
    },
    {
      code: "sw",
      message:
        "Chagua njia ya kujifunza kwanza ili kuona hatua zako zinazofuata na fursa zinazolingana.",
      link: "Chagua njia ya kujifunza",
    },
  ]) {
    await page.goto("/");
    await page.evaluate(
      (code) => localStorage.setItem("somai-language", code),
      language.code,
    );
    await page.context().clearCookies();
    await page.goto("/next");

    await expect(page.getByText(language.message)).toBeVisible();
    await expect(
      page.getByRole("link", { name: language.link }),
    ).toHaveAttribute("href", "/");
  }
});
