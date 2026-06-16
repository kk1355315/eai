import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": {
        target: "http://eai.744477.xyz",
        changeOrigin: true,
      },
    },
  },
});
