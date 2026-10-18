import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// Everything Django serves: the API, feeds, and the server-rendered public pages.
const DJANGO_PATHS = [
  "/api",
  "/feeds",
  "/sso",
  "/holidays",
  "/pricing",
  "/today",
  "/tools",
  "/widget",
  "/about",
  "/contact",
  "/privacy",
  "/terms",
  "/offline",
  "/style",
  "/theme",
  "/ur/",
  "/ar/",
  "/static",
  "/robots.txt",
  "/llms.txt",
  "/llms-full.txt",
  "/manifest.webmanifest",
  "/sw.js",
  "^/sitemap.*\\.xml$",
  // The landing page; the web app's routes start at /playground, /app, /login…
  "^/(\\?.*)?$",
];
// Keep the browser's Host so Django's CSRF origin check matches the page origin.
const django = {
  target: process.env.API_PROXY_TARGET ?? "http://127.0.0.1:8000",
  changeOrigin: false,
};

export default defineConfig({
  plugins: [react(), tailwindcss()],
  build: {
    // The CSP has no data: fonts, so small font files must stay files instead of inlined URIs.
    assetsInlineLimit: 0,
    rolldownOptions: {
      output: {
        // Libraries change far less often than the app, so they get their own cached file.
        codeSplitting: {
          groups: [
            {
              name: "vendor",
              test: /node_modules[\\/](react|react-dom|scheduler|react-router|@tanstack|i18next|react-i18next)[\\/]/,
            },
          ],
        },
      },
    },
  },
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
