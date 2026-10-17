// Wrap Latin text (rates, headers) in a left-to-right isolate so it keeps its order inside an
// Urdu or Arabic sentence; without it "120/minute" renders as "minute/120".
export function ltr(text: string): string {
  return `\u2066${text}\u2069`;
}

// Round the axis top up to 1, 2 or 5 times a power of ten, so the tick reads cleanly.
export function niceMax(value: number): number {
  if (value <= 0) return 1;
  const power = 10 ** Math.floor(Math.log10(value));
  const step = [1, 2, 5, 10].find((m) => m * power >= value) ?? 10;
  return step * power;
}
