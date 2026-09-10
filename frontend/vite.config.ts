import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const API = process.env.API_URL ?? "http://127.0.0.1:8000";

// The API sets an httponly session cookie, so the dev server proxies every API
// path under its own origin to keep that cookie same-origin.
const API_PATHS = ["/me", "/auth", "/workspace", "/workspaces"];

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: Object.fromEntries(API_PATHS.map((path) => [path, API])),
  },
  test: {
    environment: "jsdom",
    globals: true,
  },
});
