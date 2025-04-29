import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  // Same as STATIC_URL
  base: "/static/bundler/",
  plugins: [react(), tailwindcss()],
  server: {
    host: true,
    cors: true
  },
  build: {
    manifest: "manifest.json",
    outDir: "./assets",
    rollupOptions: {
      input: {
        dashboard: "/src/dashboard.tsx",
        members: "/src/members.tsx",
        style: "/src/style.css",
      },
    },
  },
});
