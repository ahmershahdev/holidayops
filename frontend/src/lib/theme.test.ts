import { afterEach, describe, expect, it } from "vitest";
import { readTheme, saveTheme } from "./theme";

describe("theme", () => {
  afterEach(() => {
    document.cookie = "theme=; path=/; max-age=0";
  });

  it("reads the theme cookie and defaults to the device", () => {
    expect(readTheme("")).toBe("system");
    expect(readTheme("csrftoken=x; theme=dark")).toBe("dark");
    expect(readTheme("theme=light; other=1")).toBe("light");
    expect(readTheme("theme=purple")).toBe("system");
    expect(readTheme("mytheme=dark")).toBe("system");
  });

  it("saves the choice and applies it to the document", () => {
    saveTheme("dark");
    expect(readTheme()).toBe("dark");
    expect(document.documentElement.dataset.theme).toBe("dark");
    saveTheme("system");
    expect(readTheme()).toBe("system");
    expect(document.documentElement.dataset.theme).toBe("system");
  });
});
