import { Crown, Flame, Gauge, Swords, Target, Zap } from 'lucide-react'

const ITEMS = [
  ['top_scorer', 'Top run-scorer', Crown, 'accent', (h) => [h.name, `${h.runs} (${h.balls})`, h.team]],
  ['top_wicket_taker', 'Top wicket-taker', Target, 'rose', (h) => [h.name, `${h.wickets}/${h.runs}`, h.team]],
  ['best_strike_rate', 'Best strike rate', Zap, 'amber', (h) => [h.name, h.strike_rate, `${h.runs} off ${h.balls} · min ${h.min_balls} balls`]],
  ['best_economy', 'Best economy', Gauge, 'sky', (h) => [h.name, h.economy, `${h.overs} ov · min ${Math.round(h.min_balls / 6)} ov`]],
  ['all_round', 'Best all-round', Swords, 'violet', (h) => [h.name, `${h.runs} runs · ${h.wickets} wkts`, h.team]],
  ['most_impactful', 'Highest contribution', Flame, 'accent', (h) => [h.name, `${h.impact} pts`, h.team]],
]
const TONE = { accent: 'text-accent bg-accent/15', rose: 'text-rose bg-rose/15', amber: 'text-amber bg-amber/15', sky: 'text-sky bg-sky/15', violet: 'text-violet bg-violet/15' }

export default function Highlights({ highlights, compact = false }) {
  const shown = ITEMS.filter(([k]) => highlights?.[k]).slice(0, compact ? 4 : 6)
  if (!shown.length) return <p className="text-sm text-mute">Not enough play yet for highlights.</p>
  return (
    <div className={`grid gap-3 ${compact ? 'sm:grid-cols-2' : 'sm:grid-cols-2 xl:grid-cols-3'}`}>
      {shown.map(([k, label, Icon, tone, fn]) => {
        const [name, big, sub] = fn(highlights[k])
        return (
          <div key={k} className="rounded-xl border border-line bg-surface2/50 p-3.5">
            <div className="flex items-center gap-2"><span className={`grid h-7 w-7 place-items-center rounded-lg ${TONE[tone]}`}><Icon size={14} /></span><span className="label">{label}</span></div>
            <div className="mt-2 truncate font-semibold">{name}</div>
            <div className="num font-display text-xl font-bold">{big}</div>
            <div className="truncate text-xs text-mute">{sub}</div>
          </div>
        )
      })}
    </div>
  )
}
