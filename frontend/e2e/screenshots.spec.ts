import { expect, test } from "./fixtures";

const SHOTS = "e2e/screenshots";

test("capture the login page", async ({ browser }) => {
  // A fresh context: no session cookie, so the API serves the sign-in page itself.
  const page = await browser.newPage();
  await page.goto("/auth/login");
  await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
  await page.screenshot({ path: `${SHOTS}/login.png`, fullPage: true });
  await page.close();
});

test("capture full-page screenshots of each view", async ({ page, seeded }) => {
  await page.goto("/");
  await expect(page.locator(".project-card").first()).toBeVisible();
  await page.screenshot({ path: `${SHOTS}/home.png`, fullPage: true });

  const views = [
    ["library", "main.main h1"],
    ["review", ".proposal-entry-actions, main.main button:has-text('Approve')"],
    ["history", "main.main h1"],
    ["members", "main.main h1"],
  ] as const;
  for (const [view, ready] of views) {
    await page.goto(`/w/${seeded.personalId}/${view}`);
    await expect(page.locator(ready).first()).toBeVisible();
    await expect(page.locator("[aria-busy='true']")).toHaveCount(0);
    await page.screenshot({ path: `${SHOTS}/${view}.png`, fullPage: true });
  }

  await page.goto(`/w/${seeded.personalId}/library`);
  await page.locator(".switcher-trigger").click();
  await expect(page.locator(".switcher-menu")).toBeVisible();
  await page.screenshot({ path: `${SHOTS}/switcher-open.png` });
});
