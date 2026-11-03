/** MatchBack AI mark: a cricket ball (seam arcs) with a match-timeline pulse running through it. */
export function LogoMark({ size = 36 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" role="img" aria-label="MatchBack AI logo" className="shrink-0">
      <rect width="64" height="64" rx="16" className="fill-surface2" />
      <circle cx="32" cy="32" r="20" fill="none" strokeWidth="3.5" className="stroke-accent" />
      <path d="M19 17c7 6 7 24 0 30M45 17c-7 6-7 24 0 30" fill="none" strokeWidth="2.2" strokeLinecap="round" className="stroke-accent" opacity=".55" />
      <path d="M6 33h13l5-10 7 19 6-14 4 5h17" fill="none" strokeWidth="3.2" strokeLinecap="round" strokeLinejoin="round" className="stroke-ink" />
    </svg>
  )
}

export default function Logo({ className = '' }) {
  return (
    <span className={`inline-flex items-center gap-2.5 ${className}`}>
      <LogoMark />
      <span className="font-display text-xl font-bold leading-none tracking-tight">
        MatchBack<span className="ml-1 rounded-md bg-accent px-1.5 py-0.5 align-middle text-[11px] font-bold text-accent-ink">AI</span>
      </span>
    </span>
  )
}
