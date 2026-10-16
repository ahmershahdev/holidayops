import type { Schemas } from "../api/client";
import { Badge } from "./ui";

const KIND_TONE = { holiday: "slate", closure: "red", half_day: "amber" } as const;

export function HolidayTable({ holidays }: { holidays: Schemas["Holiday"][] }) {
  if (holidays.length === 0) return <p className="text-sm text-slate-500">No holidays.</p>;
  return (
    <table className="w-full text-start text-sm">
      <thead className="border-b border-slate-200 text-slate-500">
        <tr>
          <th className="py-2 text-start font-medium">Date</th>
          <th className="py-2 text-start font-medium">Name</th>
          <th className="py-2 text-start font-medium">Kind</th>
        </tr>
      </thead>
      <tbody>
        {holidays.map((h) => (
          <tr key={`${h.date}-${h.name}`} className="border-b border-slate-100">
            <td className="py-2 pe-4 font-mono text-slate-700">{h.date}</td>
            <td className="py-2 pe-4 text-slate-900">{h.name}</td>
            <td className="py-2">
              <Badge tone={KIND_TONE[h.kind]}>{h.kind.replace("_", " ")}</Badge>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
