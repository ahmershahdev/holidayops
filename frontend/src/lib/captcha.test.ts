import { describe, expect, it } from "vitest";
import { checkboxSize, pageTheme } from "./captcha";

describe("captcha", () => {
  it("uses the compact checkbox when the normal one would overflow", () => {
    expect(checkboxSize(320)).toBe("normal");
    expect(checkboxSize(304)).toBe("normal");
    expect(checkboxSize(280)).toBe("compact");
  });

  it("draws the checkbox in the page's chosen theme", () => {
    const root = document.createElement("html");
    root.dataset.theme = "dark";
    expect(pageTheme(root)).toBe("dark");
    root.dataset.theme = "light";
    expect(pageTheme(root)).toBe("light");
  });
});
