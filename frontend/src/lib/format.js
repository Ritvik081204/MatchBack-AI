export const FORMAT_LABEL = { T20: 'T20', ODI: 'ODI', TEST: 'Test' }

export function fmtDate(iso) {
  if (!iso) return ''
  const d = new Date(iso + 'T00:00:00')
  return d.toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' })
}

export const KIND_STYLE = {
  LIVE: { label: 'LIVE', cls: 'border-rose/60 bg-rose/15 text-rose', dot: true },
  DEMO: { label: 'DEMO MATCH', cls: 'border-violet/60 bg-violet/15 text-violet' },
  HISTORICAL: { label: 'HISTORICAL', cls: 'border-sky/50 bg-sky/10 text-sky' },
}

export const EVENT_META = {
  wicket: { label: 'Wicket', color: 'rose' },
  six: { label: 'Six', color: 'accent' },
  four: { label: 'Four', color: 'sky' },
  milestone: { label: 'Milestone', color: 'amber' },
  big_over: { label: 'Big over', color: 'accent' },
  maiden: { label: 'Maiden', color: 'sky' },
  drs: { label: 'DRS', color: 'violet' },
  innings_break: { label: 'Innings', color: 'mute' },
  innings_start: { label: 'Innings', color: 'mute' },
  phase: { label: 'Phase', color: 'mute' },
}

export const colorText = { rose: 'text-rose', accent: 'text-accent', sky: 'text-sky', amber: 'text-amber', violet: 'text-violet', mute: 'text-mute' }
export const colorBg = { rose: 'bg-rose/15', accent: 'bg-accent/15', sky: 'bg-sky/15', amber: 'bg-amber/15', violet: 'bg-violet/15', mute: 'bg-surface2' }

export function scoreOf(match, teamName) {
  return (match.scores || []).filter((s) => s.team === teamName)
}

export const num = (v, d = 0) => (v === null || v === undefined ? '-' : Number(v).toFixed(d))
