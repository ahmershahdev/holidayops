import { useTranslation } from "react-i18next";
import { Badge } from "../ui";
import type { DayResult } from "./dayStatus";

export function StatusLine({ day }: { day: DayResult }) {
  const { t } = useTranslation();
  const tone = day.is_business_day ? (day.half_day ? "halfday" : "workday") : "holiday";
  return (
    <div className="flex flex-col gap-2" data-testid="check-result">
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone={tone}>
          {day.is_business_day ? t("status.businessDay") : t("status.dayOff")}
        </Badge>
        <span className="text-sm text-muted">{t(`reason.${day.reason}`)}</span>
      </div>
      {day.holidays.length > 0 && (
        <ul className="list-disc ps-5 text-sm" dir="auto">
          {day.holidays.map((name) => (
            <li key={name}>{name}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
