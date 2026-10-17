import { describe, expect, it } from "vitest";
import { safeNext } from "./navigation";

describe("safeNext", () => {
  it("keeps same-site paths", () => {
    expect(safeNext("/invite?token=abc")).toBe("/invite?token=abc");
    expect(safeNext("/")).toBe("/");
  });

  it.each([null, "", "https://evil.example", "//evil.example", "/\\evil.example", "app"])(
    "falls back to /app for %s",
    (value) => {
      expect(safeNext(value)).toBe("/app");
    },
  );
});
