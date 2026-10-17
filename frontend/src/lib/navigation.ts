// Only same-site paths, so a crafted link can't send people to another site after login.
// "//host" and "/\host" are both read by browsers as a different origin.
export function safeNext(value: string | null): string {
  return value && /^\/(?![/\\])/.test(value) ? value : "/app";
}
