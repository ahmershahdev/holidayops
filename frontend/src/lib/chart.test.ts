import { describe, expect, it } from "vitest";
import { ltr, niceMax } from "./chart";

describe("niceMax", () => {
  it.each([
    [0, 1],
    [1, 1],
    [3, 5],
    [7, 10],
    [10, 10],
    [11, 20],
    [240, 500],
    [999, 1000],
    [1001, 2000],
  ])("%d -> %d", (value, expected) => {
    expect(niceMax(value)).toBe(expected);
  });
});

describe("ltr", () => {
  it("wraps text in a left-to-right isolate", () => {
    expect(ltr("120/minute")).toBe("\u2066120/minute\u2069");
  });
});
