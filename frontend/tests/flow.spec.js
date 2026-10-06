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
