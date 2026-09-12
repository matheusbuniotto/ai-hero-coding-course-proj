import { expect, test } from "./fixtures";

test("projects home renders and filter chips narrow the grid", async ({ page, seeded }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Your projects" })).toBeVisible();

  const cards = page.locator(".project-card");
  const workspaceCards = page.locator(".project-card:not(.project-card-template)");
  const templateCards = page.locator(".project-card-template");
  const chip = (name: string) => page.locator(".projects-home-chip", { hasText: name });

  await expect(chip("All")).toHaveClass(/active/);
  await expect(workspaceCards).toHaveCount(2);
  await expect(templateCards).toHaveCount(6);

  await chip("Personal").click();
  await expect(chip("Personal")).toHaveClass(/active/);
  await expect(chip("All")).not.toHaveClass(/active/);
  await expect(cards).toHaveCount(1);
  await expect(cards.first()).toContainText(`${seeded.email}'s workspace`);

  await chip("Team").click();
  await expect(cards).toHaveCount(1);
  await expect(cards.first()).toContainText("E2E Team");

  await chip("Templates").click();
  await expect(workspaceCards).toHaveCount(0);
  await expect(templateCards).toHaveCount(6);

  await chip("All").click();
  await page.getByLabel("Search projects and templates").fill("team");
  await expect(cards).toHaveCount(1);
  await expect(cards.first()).toContainText("E2E Team");
});

test("clicking a workspace card opens its library", async ({ page, seeded }) => {
  await page.goto("/");
  await page.locator(".project-card", { hasText: "E2E Team" }).click();
  await expect(page).toHaveURL(new RegExp(`/w/${seeded.teamId}/library$`));
});
