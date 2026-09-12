import os from "node:os";
import path from "node:path";

import { defineConfig, devices } from "@playwright/test";

// Own ports, so a running `make dev` (real workspace.db, maybe no dev auth) is never reused.
const API_PORT = 8765;
const UI_PORT = 5174;
const API_URL = `http://127.0.0.1:${API_PORT}`;
const UI_URL = `http://127.0.0.1:${UI_PORT}`;

// A throwaway SQLite file per run; the real workspace.db is never touched.
const E2E_DB = path.join(os.tmpdir(), `icm-e2e-${Date.now()}.db`);
const REPO_ROOT = path.resolve(import.meta.dirname, "..");

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: UI_URL,
    trace: "retain-on-failure",
    viewport: { width: 1440, height: 900 },
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 } } }],
  webServer: [
    {
      command: `uv run uvicorn icm_platform.app:app --port ${API_PORT}`,
      cwd: REPO_ROOT,
      url: `${API_URL}/auth/login`,
      env: { ICM_DEV_AUTH: "1", DATABASE_URL: `sqlite:///${E2E_DB}` },
      reuseExistingServer: false,
      timeout: 60_000,
    },
    {
      command: `npm run dev -- --port ${UI_PORT} --strictPort --host 127.0.0.1`,
      url: UI_URL,
      env: { API_URL },
      reuseExistingServer: false,
      timeout: 60_000,
    },
  ],
});
