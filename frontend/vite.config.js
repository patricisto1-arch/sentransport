import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    // En local, les appels /api/... sont redirigés vers la passerelle Nginx (docker compose up)
    proxy: { "/api": "http://localhost:80" },
  },
  test: {
    environment: "jsdom",
  },
});
