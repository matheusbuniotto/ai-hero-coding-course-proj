import type { Locator } from "@playwright/test";

import { expect, test } from "./fixtures";

const css = (locator: Locator, prop: string) =>
  locator.evaluate((el, p) => getComputedStyle(el).getPropertyValue(p), prop);

test("design tokens from DESIGN.md are applied on real elements", async ({ page, seeded }) => {
  await page.goto("/");
  await expect(page.locator(".project-card").first()).toBeVisible();

  expect(await css(page.locator("body"), "background-color")).toBe("rgb(10, 10, 10)");

  const card = page.locator(".project-card").first();
  expect(await css(card, "box-shadow")).toBe("none");
  expect(await css(card, "border-radius")).toBe("8px");
  expect(await css(card, "background-color")).toBe("rgb(25, 25, 25)");

  const activeChip = page.locator(".projects-home-chip.active");
  expect(await css(activeChip, "border-radius")).toBe("9999px");
  expect(await css(activeChip, "background-color")).toBe("rgb(255, 255, 255)");

  expect(await css(page.getByRole("heading", { name: "Your projects" }), "font-weight")).toBe("400");

  await page.goto(`/w/${seeded.personalId}/review`);
  const activeTab = page.locator("nav.tabs .tab.active");
  await expect(activeTab).toHaveText(/Review/);
  expect(await css(activeTab, "border-radius")).toBe("9999px");

  const approve = page.getByRole("button", { name: "Approve" });
  await expect(approve).toBeVisible();
  expect(await css(approve, "border-radius")).toBe("9999px");
  expect(await css(approve, "background-color")).toBe("rgb(255, 255, 255)");

  for (const heading of await page.locator("h1, h2, h3").all()) {
    expect(await css(heading, "font-weight"), await heading.textContent() ?? "").toBe("400");
  }
});
