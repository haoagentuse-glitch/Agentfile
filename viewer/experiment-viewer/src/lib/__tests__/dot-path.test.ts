import { describe, expect, it } from "vitest";
import { getByPath, getNumberRecordByPath, getStringByPath } from "../dot-path";

describe("getByPath", () => {
  it("resolves nested keys", () => {
    expect(getByPath({ a: { b: { c: 42 } } }, "a.b.c")).toBe(42);
  });

  it("returns undefined for missing keys", () => {
    expect(getByPath({ a: { b: 1 } }, "a.x.y")).toBeUndefined();
  });

  it("returns undefined when traversing through a non-object", () => {
    expect(getByPath({ a: 1 }, "a.b")).toBeUndefined();
  });

  it("returns undefined for an empty path", () => {
    expect(getByPath({ a: 1 }, "")).toBeUndefined();
  });

  it("does not support array indices or wildcards (restricted dot-path only)", () => {
    expect(getByPath({ a: [1, 2, 3] }, "a.0")).toBeUndefined();
    expect(getByPath({ a: [1, 2, 3] }, "a.*")).toBeUndefined();
  });
});

describe("getStringByPath", () => {
  it("returns the string at path", () => {
    expect(getStringByPath({ meta: { title: "hello" } }, "meta.title")).toBe("hello");
  });

  it("returns undefined when the value is not a string", () => {
    expect(getStringByPath({ meta: { title: 42 } }, "meta.title")).toBeUndefined();
  });

  it("returns undefined when path is undefined", () => {
    expect(getStringByPath({ meta: { title: "hello" } }, undefined)).toBeUndefined();
  });
});

describe("getNumberRecordByPath", () => {
  it("keeps only numeric entries", () => {
    expect(getNumberRecordByPath({ metrics: { a: 1, b: "x", c: 2.5 } }, "metrics")).toEqual({ a: 1, c: 2.5 });
  });

  it("returns empty object when path is missing or not an object", () => {
    expect(getNumberRecordByPath({ metrics: 5 }, "metrics")).toEqual({});
    expect(getNumberRecordByPath({}, undefined)).toEqual({});
  });
});
