import { resolve } from "node:path";
import { defineConfig } from "vite";

// Where /pool/* goes: the hosted miner (run_all.sh sets POOL_TARGET) or the practice server.
const poolProxy = {
  "/pool": {
    target: process.env.POOL_TARGET ?? "http://127.0.0.1:8091",
    changeOrigin: true,
    rewrite: (path: string) => path.replace(/^\/pool/, ""),
  },
};

export default defineConfig({
  server: {
    port: 5173,
    allowedHosts: true,
    // Same-origin pool for HTTPS tunnels: the page calls /pool/* and Vite forwards it.
    proxy: poolProxy,
  },
  preview: { proxy: poolProxy },
  build: {
    target: "es2022",
    chunkSizeWarningLimit: 4000,
    rollupOptions: {
      input: {
        main: resolve(__dirname, "index.html"),
        play: resolve(__dirname, "play.html"),
        network: resolve(__dirname, "network.html"),
      },
    },
  },
  optimizeDeps: { exclude: ["@mujoco/mujoco"] },
});
