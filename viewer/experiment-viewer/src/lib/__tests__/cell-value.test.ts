import { describe, expect, it } from "vitest";

import { MAX_CELL_CHARS, toCellView, toComparable, toSearchText } from "../cell-value";

describe("toCellView", () => {
  it("shows a distinct placeholder for null, undefined and empty string", () => {
    for (const value of [null, undefined, ""]) {
      const view = toCellView(value);
      expect(view.kind).toBe("empty");
      expect(view.text).toBe("—");
    }
  });

  it("never renders an object as [object Object]", () => {
    const view = toCellView({ id: 1, title: "第一則", body: "內容", tags: [] });

    expect(view.text).not.toContain("[object Object]");
    expect(view.kind).toBe("object");
    expect(view.text).toBe("{ id, title, body, tags }");
  });

  it("gives a full JSON payload for objects so the detail is reachable", () => {
    const view = toCellView({ a: 1 });

    expect(view.full).toBe(JSON.stringify({ a: 1 }, null, 2));
  });

  it("marks empty containers explicitly instead of showing nothing", () => {
    expect(toCellView([]).text).toBe("[]（空陣列）");
    expect(toCellView({}).text).toBe("{}（空物件）");
  });

  it("lists scalar arrays inline and summarises object arrays by count", () => {
    expect(toCellView(["a", "b", 3]).text).toBe("a, b, 3");
    expect(toCellView([{ a: 1 }, { a: 2 }]).text).toBe("2 筆");
  });

  it("truncates a long string and keeps the full value reachable", () => {
    const long = "字".repeat(MAX_CELL_CHARS + 50);

    const view = toCellView(long);

    expect(view.truncated).toBe(true);
    expect(view.text.length).toBe(MAX_CELL_CHARS + 1); // 截斷後加一個省略號
    expect(view.full).toBe(long);
  });

  it("does not truncate a string that fits", () => {
    const view = toCellView("剛好夠短");

    expect(view.truncated).toBe(false);
    expect(view.full).toBeUndefined();
  });

  it("shows NaN and Infinity faithfully rather than blanking them", () => {
    // 這是真的出現過的資料問題，靜默變成 0 或空白會讓它更難發現。
    expect(toCellView(Number.NaN).text).toBe("NaN");
    expect(toCellView(Number.POSITIVE_INFINITY).text).toBe("Infinity");
  });

  it("keeps false visible instead of treating it as missing", () => {
    const view = toCellView(false);

    expect(view.kind).toBe("boolean");
    expect(view.text).toBe("false");
  });

  it("keeps zero visible instead of treating it as missing", () => {
    expect(toCellView(0).text).toBe("0");
  });
});

describe("toComparable", () => {
  it("keeps numbers numeric so sorting is not lexicographic", () => {
    expect(toComparable(10)).toBe(10);
    expect(toComparable(2)).toBe(2);
  });

  it("never throws on an unknown or cyclic structure", () => {
    const cyclic: Record<string, unknown> = {};
    cyclic.self = cyclic;

    expect(() => toComparable(cyclic)).not.toThrow();
    expect(toComparable(cyclic)).toBe("[circular]");
  });

  it("treats missing values as an empty string so they group together", () => {
    expect(toComparable(null)).toBe("");
    expect(toComparable(undefined)).toBe("");
  });
});

describe("toSearchText", () => {
  it("finds text inside objects and arrays, not only scalars", () => {
    expect(toSearchText({ title: "檢索覆蓋率" })).toContain("檢索覆蓋率");
    expect(toSearchText(["Alpha", "Beta"])).toContain("alpha");
  });
});
