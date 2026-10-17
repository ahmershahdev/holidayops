// The logo mark (simplified H + flight path) and two-tone wordmark; same as
// backend/apps/public/templates/public/_mark.html.
export function Mark({ className = "size-8" }: { className?: string }) {
  return (
    <svg viewBox="0 0 40 40" aria-hidden="true" focusable="false" className={`mark ${className}`}>
      <rect x="6" y="5" width="9" height="30" rx="3" className="fill-glow" />
      <rect x="25" y="5" width="9" height="30" rx="3" fill="currentColor" />
      <path
        d="M3 31 C 11 19, 23 18, 36 12"
        fill="none"
        strokeWidth="4"
        strokeLinecap="round"
        className="stroke-accent"
      />
      <path d="M33 9.5 l5 1.6 -4.2 3.1 z" fill="currentColor" className="mark-plane" />
    </svg>
  );
}

export function Wordmark() {
  return (
    <span dir="ltr" className="font-display font-bold tracking-tight">
      Holiday<span className="text-accent">Ops</span>
    </span>
  );
}
