import { describe, expect, it } from "vitest";
import { formatIncludesUnit, formatMetricValue } from "../metric-format";

describe("formatMetricValue", () => {
  it("renders manifest .N% formats as percentages", () => {
    expect(formatMetricValue(0.9, ".2%")).toBe("90.00%");
    expect(formatIncludesUnit(".2%")).toBe(false);
  });

  it("renders fixed decimals and keeps their unit", () => {
    expect(formatMetricValue(1.234, ".2f")).toBe("1.23");
    expect(formatIncludesUnit(".2f")).toBe(true);
  });

  it("falls back without guessing an unknown or unsafe format", () => {
    expect(formatMetricValue(1.2, "scientific")).toBe("1.2");
    expect(formatMetricValue(0.9, ".101%")).toBe("0.9");
    expect(formatIncludesUnit(".101%")).toBe(true);
    expect(formatMetricValue(null, ".2%")).toBe("—");
  });
});