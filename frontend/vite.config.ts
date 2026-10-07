import { fileURLToPath, URL } from "node:url";

import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// In Docker the API is reachable as http://api:8000; locally as http://localhost:8000.
const apiTarget = process.env.API_PROXY_TARGET ?? "http://localhost:8000";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },
  server: {
    host: "0.0.0.0",
    port: 5173,
    strictPort: true,
    // "frontend" is the Docker Compose service name used by the end-to-end tests.
    allowedHosts: ["localhost", "frontend"],
    // Same-origin calls in development too: the browser never talks to the API directly.
    proxy: {
      "/api": { target: apiTarget, xfwd: true },
      "/health": { target: apiTarget },
    },
  },
  build: {
    // Fonts stay separate files: the production CSP allows fonts from 'self' only, not data: URIs
    // (small font subsets would otherwise be inlined).
    assetsInlineLimit: (filePath) => (/\.(woff2?|ttf|otf)$/.test(filePath) ? false : undefined),
  },
  preview: { host: "0.0.0.0", port: 4173 },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
    css: false,
  },
});
