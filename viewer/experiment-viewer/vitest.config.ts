import vue from "@vitejs/plugin-vue";
import { defineConfig } from "vitest/config";

// 兩種測試共存：
// - src/lib/**：純邏輯（adapter、dot-path、project-loader、cell-value），node environment 就夠。
// - src/components/** 與 src/views/**：真的掛載元件，需要 jsdom。
//   資料層測試不能取代元件測試——排序、篩選、缺值與物件欄位的顯示規則
//   只有掛起來才驗得到。
export default defineConfig({
  plugins: [vue()],
  test: {
    include: ["src/**/*.test.ts"],
    environmentMatchGlobs: [
      ["src/components/**", "jsdom"],
      ["src/views/**", "jsdom"],
    ],
  },
});
