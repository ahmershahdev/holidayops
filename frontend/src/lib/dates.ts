// Weekdays follow Python's numbering (Monday = 0) because that is what the API returns.

export type ISODate = string;

export function toISO(year: number, month: number, day: number): ISODate {
  return `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
}

export function parseISO(value: ISODate): { year: number; month: number; day: number } {
  const [year = 0, month = 1, day = 1] = value.split("-").map(Number);
  return { year, month, day };
}

export function daysInMonth(year: number, month: number): number {
  return new Date(Date.UTC(year, month, 0)).getUTCDate();
}

export function pythonWeekday(value: ISODate): number {
  const { year, month, day } = parseISO(value);
  return (new Date(Date.UTC(year, month - 1, day)).getUTCDay() + 6) % 7;
}

export function addDays(value: ISODate, days: number): ISODate {
  const { year, month, day } = parseISO(value);
  const d = new Date(Date.UTC(year, month - 1, day + days));
  return toISO(d.getUTCFullYear(), d.getUTCMonth() + 1, d.getUTCDate());
}

export function addMonths(
  year: number,
  month: number,
  delta: number,
): { year: number; month: number } {
  const index = year * 12 + (month - 1) + delta;
  return { year: Math.floor(index / 12), month: (index % 12) + 1 };
}

export function weekStartFor(weekend: readonly number[]): number {
  const days = new Set(weekend);
  for (const day of days) {
    const next = (day + 1) % 7;
    if (!days.has(next)) return next;
  }
  return 0;
}

export function monthMatrix(year: number, month: number, weekStart: number): (ISODate | null)[][] {
  const first = toISO(year, month, 1);
  const lead = (pythonWeekday(first) - weekStart + 7) % 7;
  const cells: (ISODate | null)[] = Array.from({ length: lead }, () => null);
  for (let day = 1; day <= daysInMonth(year, month); day++) cells.push(toISO(year, month, day));
  while (cells.length % 7 !== 0) cells.push(null);
  const weeks: (ISODate | null)[][] = [];
  for (let i = 0; i < cells.length; i += 7) weeks.push(cells.slice(i, i + 7));
  return weeks;
}

export function orderedWeekdays(weekStart: number): number[] {
  return Array.from({ length: 7 }, (_, i) => (weekStart + i) % 7);
}

export function todayISO(): ISODate {
  const now = new Date();
  return toISO(now.getFullYear(), now.getMonth() + 1, now.getDate());
}
