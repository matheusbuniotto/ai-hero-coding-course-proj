import { expect, test } from "./fixtures";

test("workspace tabs render and navigate between views", async ({ page, seeded }) => {
  await page.goto(`/w/${seeded.personalId}`);
  await expect(page).toHaveURL(new RegExp(`/w/${seeded.personalId}/library$`));

  const tabs = page.locator("nav.tabs .tab");
  await expect(tabs).toHaveText(["Library", /^Review\s*1$/, "History", "Members"]);

  for (const [label, slug] of [
    ["Review", "review"],
    ["History", "history"],
    ["Members", "members"],
    ["Library", "library"],
  ] as const) {
    const tab = tabs.filter({ hasText: label });
    await tab.click();
    await expect(page).toHaveURL(new RegExp(`/w/${seeded.personalId}/${slug}$`));
    await expect(tab).toHaveClass(/active/);
    const heading = slug === "library" ? `${seeded.email}'s workspace` : label;
    await expect(page.locator("main.main h1")).toHaveText(heading);
  }
});

test("sidebar lists agents and files, and opening a file shows it", async ({ page, seeded }) => {
  await page.goto(`/w/${seeded.personalId}/library`);
  const sidebar = page.locator("aside.sidebar");
  await expect(sidebar.getByRole("heading", { name: "Agents" })).toBeVisible();
  await expect(sidebar.getByRole("heading", { name: "Files" })).toBeVisible();

  await expect(sidebar.getByRole("list", { name: "Agents" }).getByRole("button")).toHaveText(["writer"]);
  const files = sidebar.getByRole("list", { name: "Files" });
  await expect(files.locator(".file-link", { hasText: "intro.md" })).toContainText("in review");
  await expect(files.locator(".file-link", { hasText: "prompt.md" })).toBeVisible();

  await files.locator(".file-link", { hasText: "intro.md" }).click();
  await expect(page.locator("pre.document")).toContainText("Hello world.");
});

test("chat column hides and comes back through the status bar", async ({ page, seeded }) => {
  await page.goto(`/w/${seeded.personalId}/library`);
  const chat = page.getByRole("complementary", { name: "Agent session" }).or(page.locator(".chat-column"));
  const statusbar = page.getByRole("contentinfo", { name: "Closed panes" });

  await expect(chat).toBeVisible();
  await statusbar.getByRole("button", { name: "Show Sandbox output" }).waitFor();
  await expect(statusbar.getByRole("button", { name: "Show Chat" })).toHaveCount(0);

  // Chat can't be hidden while it's the only open pane; open the file first.
  await page.locator(".file-link", { hasText: "intro.md" }).click();
  await page.getByRole("button", { name: "Hide chat" }).click();
  await expect(chat).toHaveCount(0);
  await expect(page).toHaveURL(/chat=hidden/);

  await statusbar.getByRole("button", { name: "Show Chat" }).click();
  await expect(chat).toBeVisible();
  await expect(statusbar.getByRole("button", { name: "Show Chat" })).toHaveCount(0);
});

test("workspace switcher opens a menu to switch workspaces", async ({ page, seeded }) => {
  await page.goto(`/w/${seeded.personalId}/library`);
  const trigger = page.locator(".switcher-trigger");
  await expect(trigger).toContainText(`${seeded.email}'s workspace`);

  await trigger.click();
  const menu = page.getByRole("dialog", { name: "Switch workspace" });
  await expect(menu.getByRole("list", { name: "Workspaces" }).getByRole("button")).toHaveCount(2);

  await page.keyboard.press("Escape");
  await expect(menu).toHaveCount(0);

  await trigger.click();
  await menu.locator(".switcher-item:not(.active)").click();
  await expect(page).not.toHaveURL(new RegExp(`/w/${seeded.personalId}/`));
  await expect(menu).toHaveCount(0);
});
