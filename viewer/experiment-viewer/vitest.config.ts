import vue from "@vitejs/plugin-vue";
import { defineConfig } from "vitest/config";

// 資料層需要 Node 的真實 file: URL；元件與 view 需要 jsdom。
// Vitest 4 以 inline projects 取代舊版 environmentMatchGlobs。
export default defineConfig({
  test: {
    projects: [
      {
        test: {
          name: "logic",
          include: ["src/lib/**/*.test.ts"],
          environment: "node",
        },
      },
      {
        plugins: [vue()],
        test: {
          name: "ui",
          include: ["src/components/**/*.test.ts", "src/views/**/*.test.ts"],
          environment: "jsdom",
        },
      },
    ],
  },
});
