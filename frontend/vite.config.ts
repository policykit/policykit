import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";

// https://vite.dev/config/
export default defineConfig({
  // Same as STATIC_URL
  base: "/static/bundler/",
  plugins: [react()],
  server: {
    host: true,
    origin: 'http://localhost:5173',
  },
  build: {
    manifest: "manifest.json",
    outDir: "./assets",
    rollupOptions: {
      input: {
        dashboard: "/src/dashboard.tsx",
      },
    },
  },
});
