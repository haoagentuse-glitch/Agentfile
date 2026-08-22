import { describe, expect, it } from "vitest";
import { statusLabel } from "../status-label";

describe("statusLabel", () => {
  it("以中文顯示已知狀態並保留原碼", () => {
    expect(statusLabel("confounded")).toBe("已混雜（confounded）");
    expect(statusLabel("invalid")).toBe("無效（invalid）");
    expect(statusLabel("fully_supported")).toBe("已支援（fully_supported）");
    expect(statusLabel("archived")).toBe("已封存（archived）");
  });

  it("忠實顯示未知 enum", () => {
    expect(statusLabel("future_status")).toBe("future_status");
  });
});
