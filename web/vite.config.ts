import { defineConfig } from "vite";

export default defineConfig({
  server: { port: 5173, allowedHosts: true },
  build: { target: "es2022", chunkSizeWarningLimit: 4000 },
  optimizeDeps: { exclude: ["@mujoco/mujoco"] },
});
