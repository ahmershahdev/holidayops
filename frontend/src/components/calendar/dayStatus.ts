import type { Schemas } from "../../api/client";

export type DayResult = Schemas["CheckResult"];
export type Tone = "workday" | "weekend" | "holiday" | "closure" | "halfday" | "moved";

export function toneOf(day: DayResult, holidayVisible: boolean): Tone {
  switch (day.reason) {
    case "holiday":
      return holidayVisible ? "holiday" : "workday";
    case "closure":
      return "closure";
    case "half_day":
      return "halfday";
    case "weekend":
      return "weekend";
    case "weekend_workday":
    case "custom_working_day":
      return "moved";
    default:
      return "workday";
  }
}

export const TONE_CELL: Record<Tone, string> = {
  workday: "bg-surface",
  weekend: "bg-weekend text-muted",
  holiday: "bg-holiday-soft text-holiday",
  closure: "bg-closure-soft text-closure",
  halfday: "bg-halfday-soft text-halfday",
  moved: "bg-workday-soft text-workday",
};

export const TONE_DOT: Record<Tone, string> = {
  workday: "bg-line/60",
  weekend: "bg-weekend-strong",
  holiday: "bg-holiday",
  closure: "bg-closure",
  halfday: "bg-halfday",
  moved: "bg-workday",
};
