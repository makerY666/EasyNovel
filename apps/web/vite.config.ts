import { env } from "node:process";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      "/api": {
        target: env.EASYNOVEL_PROXY_TARGET || "http://127.0.0.1:8765",
        changeOrigin: true,
      },
    },
  },
  build: {
    target: "es2022",
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes("/node_modules/")) {
            if (id.includes("@tiptap") || id.includes("prosemirror"))
              return "editor";
            if (id.includes("react") || id.includes("@radix-ui")) return "ui";
          }
        },
      },
    },
  },
});
