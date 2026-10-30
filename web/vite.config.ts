import { defineConfig } from "vite";

export default defineConfig({
  server: {
    port: 5173,
    allowedHosts: true,
    proxy: {
      // Same-origin pool for HTTPS tunnels: the page calls /pool/* and Vite forwards to practice/miner.
      "/pool": { target: "http://127.0.0.1:8091", changeOrigin: true, rewrite: (path) => path.replace(/^\/pool/, "") },
    },
  },
  preview: {
    proxy: {
      "/pool": { target: "http://127.0.0.1:8091", changeOrigin: true, rewrite: (path) => path.replace(/^\/pool/, "") },
    },
  },
  build: { target: "es2022", chunkSizeWarningLimit: 4000 },
  optimizeDeps: { exclude: ["@mujoco/mujoco"] },
});
