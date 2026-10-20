import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// dev: proxy /api -> FastAPI (เบราว์เซอร์ไม่รู้จัก SEC key / .env)
export default defineConfig(({ mode }) => ({
  base: mode === "static" ? "./" : "/",
  plugins: [react(), tailwindcss()],
  server: { port: 5173, proxy: { "/api": `http://127.0.0.1:${process.env.API_PORT ?? "8000"}` } },
  build: { chunkSizeWarningLimit: 900 },
}));
