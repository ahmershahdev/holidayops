import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// Everything Django serves: the API, feeds, and the server-rendered public pages.
const DJANGO_PATHS = [
  "/api",
  "/feeds",
  "/holidays",
  "/pricing",
  "/ur/",
  "/ar/",
  "/static",
  "/robots.txt",
  "^/sitemap.*\\.xml$",
];
// Keep the browser's Host so Django's CSRF origin check matches the page origin.
const django = {
  target: process.env.API_PROXY_TARGET ?? "http://127.0.0.1:8000",
  changeOrigin: false,
};

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: Object.fromEntries(DJANGO_PATHS.map((path) => [path, django])),
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test-setup.ts"],
  },
});
