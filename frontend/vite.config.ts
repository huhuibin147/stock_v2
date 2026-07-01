import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
  plugins: [vue()],
  base: process.env.NODE_ENV === "production" ? "/stock/" : "/",
  server: {
    port: 35173,
    proxy: {
      "/api": {
        target: "http://localhost:38080",
        changeOrigin: true,
      },
      "/health": {
        target: "http://localhost:38080",
        changeOrigin: true,
      },
    },
  },
});
