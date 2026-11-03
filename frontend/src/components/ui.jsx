import { AlertTriangle, Inbox, Loader2, RefreshCw } from 'lucide-react'
import { KIND_STYLE } from '../lib/format'

export function DataBadge({ kind, className = '', small = false }) {
  const s = KIND_STYLE[kind] || KIND_STYLE.HISTORICAL
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 ${small ? 'py-0.5 text-[10px]' : 'py-1 text-[11px]'} font-bold tracking-wider ${s.cls} ${className}`}>
      {s.dot && <span className="h-1.5 w-1.5 animate-pulseDot rounded-full bg-current" />}
      {s.label}
    </span>
  )
}

/** Generated abbreviation badge (no flags / third-party logos). Colour is derived from the team name. */
export function TeamBadge({ team, size = 40 }) {
  const abbr = team?.abbr || '?'
  let h = 0
  for (const ch of team?.name || '') h = (h * 31 + ch.charCodeAt(0)) % 360
  return (
    <span
      className="inline-flex shrink-0 items-center justify-center rounded-xl font-display font-bold text-white"
      style={{ width: size, height: size, fontSize: size * 0.32, background: `linear-gradient(135deg, hsl(${h} 55% 38%), hsl(${(h + 40) % 360} 60% 28%))` }}
      aria-hidden="true"
    >
      {abbr}
    </span>
  )
}

export function Loading({ label = 'Loading...', rows = 3 }) {
  return (
    <div role="status" aria-live="polite" className="space-y-3">
      <span className="sr-only">{label}</span>
      {Array.from({ length: rows }).map((_, i) => <div key={i} className="skeleton h-24" style={{ opacity: 1 - i * 0.2 }} />)}
    </div>
  )
}

export function Spinner({ className = '' }) {
  return <Loader2 className={`animate-spin ${className}`} size={16} aria-hidden="true" />
}

export function ErrorBox({ message, onRetry }) {
  return (
    <div role="alert" className="card-pad flex flex-col items-start gap-3 border-rose/40 bg-rose/10">
      <div className="flex items-center gap-2 font-semibold text-rose"><AlertTriangle size={18} /> Couldn't load this</div>
      <p className="text-sm text-mute">{message}</p>
      {onRetry && <button onClick={onRetry} className="btn btn-ghost"><RefreshCw size={14} /> Try again</button>}
    </div>
  )
}

export function Empty({ title, children, icon: Icon = Inbox }) {
  return (
    <div className="card-pad flex flex-col items-center gap-2 py-10 text-center">
      <Icon className="text-mute" size={28} />
      <div className="font-display text-lg font-semibold">{title}</div>
      {children && <div className="max-w-md text-sm text-mute">{children}</div>}
    </div>
  )
}

export function Notice({ tone = 'info', children, className = '' }) {
  const t = { info: 'border-sky/40 bg-sky/10 text-sky', warn: 'border-amber/40 bg-amber/10 text-amber', demo: 'border-violet/40 bg-violet/10 text-violet' }[tone]
  return <div className={`rounded-xl border px-4 py-3 text-sm ${t} ${className}`}>{children}</div>
}

export function SectionTitle({ eyebrow, title, children, className = '' }) {
  return (
    <div className={`mb-5 ${className}`}>
      {eyebrow && <div className="label mb-1 text-accent">{eyebrow}</div>}
      <h2 className="font-display text-2xl font-bold sm:text-3xl">{title}</h2>
      {children && <p className="mt-2 max-w-2xl text-sm text-mute">{children}</p>}
    </div>
  )
}

export function Stat({ label, value, sub, accent = false }) {
  return (
    <div className="rounded-xl border border-line bg-surface2/60 p-3">
      <div className="label">{label}</div>
      <div className={`num mt-1 font-display text-2xl font-bold ${accent ? 'text-accent' : ''}`}>{value ?? '-'}</div>
      {sub && <div className="mt-0.5 text-xs text-mute">{sub}</div>}
    </div>
  )
}
