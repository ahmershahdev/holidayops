import { useTranslation } from "react-i18next";
import { TONE_DOT, type Tone } from "./dayStatus";

const ITEMS: { tone: Tone; key: string }[] = [
  { tone: "holiday", key: "legend.holiday" },
  { tone: "closure", key: "legend.closure" },
  { tone: "halfday", key: "legend.halfDay" },
  { tone: "weekend", key: "legend.weekend" },
  { tone: "moved", key: "legend.extraWorkingDay" },
];

export function Legend() {
  const { t } = useTranslation();
  return (
    <ul className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted">
      {ITEMS.map((item) => (
        <li key={item.tone} className="flex items-center gap-1.5">
          <span
            aria-hidden
            className={`size-3 rounded-[3px] border border-line ${TONE_DOT[item.tone]}`}
          />
          {t(item.key)}
        </li>
      ))}
    </ul>
  );
}
