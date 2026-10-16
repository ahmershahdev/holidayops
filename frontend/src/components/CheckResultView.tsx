import type { Schemas } from "../api/client";
import { Badge } from "./ui";

const REASON_LABELS: Record<Schemas["ReasonEnum"], string> = {
  working_day: "Working day",
  weekend: "Weekend",
  holiday: "Holiday",
  weekend_workday: "Weekend moved to a working day",
  closure: "Company closure",
  half_day: "Half day",
  custom_working_day: "Extra working day",
};

export function CheckResultView({ result }: { result: Schemas["CheckResult"] }) {
  return (
    <div className="flex flex-col gap-2" data-testid="check-result">
      <div className="flex items-center gap-2">
        <Badge tone={result.is_business_day ? (result.half_day ? "amber" : "green") : "red"}>
          {result.is_business_day ? "Business day" : "Not a business day"}
        </Badge>
        <span className="text-sm text-slate-600">{REASON_LABELS[result.reason]}</span>
      </div>
      {result.holidays.length > 0 && (
        <ul className="list-disc ps-5 text-sm text-slate-700">
          {result.holidays.map((name) => (
            <li key={name}>{name}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
