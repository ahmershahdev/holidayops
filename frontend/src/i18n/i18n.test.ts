import { describe, expect, it } from "vitest";
import ar from "./ar.json";
import en from "./en.json";
import { holidayLanguage } from "./index";
import ur from "./ur.json";

const PLURAL = /_(zero|one|two|few|many|other)$/;

function keys(tree: object, prefix = ""): string[] {
  return Object.entries(tree).flatMap(([key, value]) =>
    typeof value === "object" && value !== null
      ? keys(value as object, `${prefix}${key}.`)
      : [`${prefix}${key}`.replace(PLURAL, "")],
  );
}

describe("translations", () => {
  const english = new Set(keys(en));

  it.each([
    ["ur", ur],
    ["ar", ar],
  ])("%s has exactly the English keys", (_, catalog) => {
    expect(new Set(keys(catalog))).toEqual(english);
  });

  it("keeps placeholders in every language", () => {
    const placeholders = (s: string) => [...s.matchAll(/{{(\w+)}}/g)].map((m) => m[1]).sort();
    const flat = (tree: object, prefix = ""): [string, string][] =>
      Object.entries(tree).flatMap(([k, v]) =>
        typeof v === "object" && v !== null
          ? flat(v as object, `${prefix}${k}.`)
          : [[`${prefix}${k}`, String(v)]],
      );
    const english = new Map(flat(en).map(([k, v]) => [k.replace(PLURAL, ""), placeholders(v)]));
    for (const catalog of [ur, ar]) {
      for (const [key, value] of flat(catalog)) {
        const expected = english.get(key.replace(PLURAL, "")) ?? [];
        const found = placeholders(value);
        expect(
          found.every((p) => expected.includes(p)),
          `${key}: ${value}`,
        ).toBe(true);
      }
    }
  });
});

describe("holidayLanguage", () => {
  it("picks a supported language for the UI language", () => {
    expect(holidayLanguage("ur", ["en_PK", "en_US", "ur_PK"], "en_PK")).toBe("ur_PK");
    expect(holidayLanguage("ar", ["ar", "en_US"], "ar")).toBe("ar");
    expect(holidayLanguage("en", ["ar", "en_US"], "ar")).toBe("en_US");
    expect(holidayLanguage("en", ["en_PK", "en_US"], "en_PK")).toBe("en_PK");
    expect(holidayLanguage("ur", ["de", "en_US"], "de")).toBeUndefined();
  });
});
