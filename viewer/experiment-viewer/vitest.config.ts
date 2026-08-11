import { defineConfig } from "vitest/config";

// 只測 src/lib/ 下的純邏輯（adapter、dot-path、project-loader），不測 Vue 元件渲染，
// 所以維持預設 node environment，不加 jsdom 依賴。
export default defineConfig({
  test: {
    include: ["src/**/*.test.ts"],
  },
});
