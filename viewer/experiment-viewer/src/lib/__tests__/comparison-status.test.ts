import { describe, expect, it } from "vitest";
import { describeComparisonStatus } from "../comparison-status";

describe("describeComparisonStatus", () => {
  it("returns confounded when confounded is true", () => {
    expect(describeComparisonStatus({ confounded: true, comparisonValid: false })).toBe("confounded");
  });

  it("returns invalid when comparisonValid is false but confounded is false — not the same as confounded", () => {
    expect(describeComparisonStatus({ confounded: false, comparisonValid: false })).toBe("invalid");
  });

  it("returns valid when comparisonValid is true and confounded is false", () => {
    expect(describeComparisonStatus({ confounded: false, comparisonValid: true })).toBe("valid");
  });

  it("treats confounded as taking priority even if comparisonValid were somehow true", () => {
    expect(describeComparisonStatus({ confounded: true, comparisonValid: true })).toBe("confounded");
  });
});
