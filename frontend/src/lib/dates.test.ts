import { describe, expect, it } from "vitest";
import {
  addDays,
  addMonths,
  daysInMonth,
  monthMatrix,
  orderedWeekdays,
  pythonWeekday,
  weekStartFor,
} from "./dates";

describe("dates", () => {
  it("uses Python weekday numbers", () => {
    expect(pythonWeekday("2027-03-22")).toBe(0);
    expect(pythonWeekday("2027-03-28")).toBe(6);
  });

  it("starts the week after the weekend", () => {
    expect(weekStartFor([5, 6])).toBe(0);
    expect(weekStartFor([4, 5])).toBe(6);
    expect(weekStartFor([6])).toBe(0);
    expect(weekStartFor([])).toBe(0);
    expect(orderedWeekdays(6)).toEqual([6, 0, 1, 2, 3, 4, 5]);
  });

  it("builds month grids aligned to the week start", () => {
    const monday = monthMatrix(2027, 3, 0);
    expect(monday[0]).toEqual([
      "2027-03-01",
      "2027-03-02",
      "2027-03-03",
      "2027-03-04",
      "2027-03-05",
      "2027-03-06",
      "2027-03-07",
    ]);
    const sunday = monthMatrix(2027, 3, 6);
    expect(sunday[0]?.[0]).toBeNull();
    expect(sunday[0]?.[1]).toBe("2027-03-01");
    expect(sunday.every((week) => week.length === 7)).toBe(true);
  });

  it("handles month and leap-year arithmetic", () => {
    expect(daysInMonth(2028, 2)).toBe(29);
    expect(addMonths(2027, 12, 1)).toEqual({ year: 2028, month: 1 });
    expect(addMonths(2027, 1, -1)).toEqual({ year: 2026, month: 12 });
    expect(addDays("2027-12-31", 1)).toBe("2028-01-01");
    expect(addDays("2027-03-01", -1)).toBe("2027-02-28");
  });
});
