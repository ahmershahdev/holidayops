import { useTranslation } from "react-i18next";
import type { Schemas } from "../../api/client";
import { useFormat } from "../../lib/format";
import { Badge } from "../ui";

const KIND_TONE = { holiday: "holiday", closure: "closure", half_day: "halfday" } as const;

export function HolidayList({ holidays }: { holidays: Schemas["Holiday"][] }) {
  const { t } = useTranslation();
  const fmt = useFormat();
  if (holidays.length === 0)
    return <p className="text-sm text-muted">{t("calendar.noHolidays")}</p>;
  return (
    <ul className="divide-y divide-line">
      {holidays.map((h) => (
        <li
          key={`${h.date}-${h.name}`}
          className="flex flex-wrap items-center gap-x-4 gap-y-1 py-3"
        >
          <time dateTime={h.date} className="w-40 shrink-0 text-sm text-muted">
            {fmt.shortDate(h.date)}
          </time>
          <span className="min-w-0 flex-1" dir="auto">
            {h.name}
          </span>
          <span className="flex gap-1.5">
            {h.sources.map((s) => (
              <Badge key={s} tone="neutral">
                {s}
              </Badge>
            ))}
            <Badge tone={KIND_TONE[h.kind]}>{t(`kind.${h.kind}`)}</Badge>
          </span>
        </li>
      ))}
    </ul>
  );
}
