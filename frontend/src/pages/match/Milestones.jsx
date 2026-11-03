import { useState } from 'react'
import { Award, Crosshair, Info, Target, Users } from 'lucide-react'
import { Empty, ErrorBox, Loading } from '../../components/ui'
import { useMatchCtx } from '../../lib/matchContext'
import { api } from '../../lib/api'
import { useApi } from '../../lib/hooks'

const CATS = [['all', 'All'], ['batting', 'Batting'], ['bowling', 'Bowling'], ['partnership', 'Partnerships'], ['team', 'Team']]
const STYLE = {
  batting: { icon: Award, tone: 'text-accent', bg: 'bg-accent/10 border-accent/40' },
  bowling: { icon: Target, tone: 'text-rose', bg: 'bg-rose/10 border-rose/40' },
  partnership: { icon: Users, tone: 'text-sky', bg: 'bg-sky/10 border-sky/40' },
  team: { icon: Crosshair, tone: 'text-amber', bg: 'bg-amber/10 border-amber/40' },
}

function chips(m) {
  const s = m.stats
  const out = []
  if (s.runs != null && m.category === 'batting') out.push(`${s.runs} runs`, `${s.balls} balls`, `${s.fours}×4`, `${s.sixes}×6`, s.strike_rate != null && `SR ${s.strike_rate}`)
  if (m.category === 'bowling') out.push(`${s.wickets} wkts`, s.runs != null && `${s.runs} runs`)
  if (m.category === 'partnership') out.push(`${s.runs} runs`, `${s.balls} balls`, `wicket ${s.wicket_no}`)
  if (m.category === 'team') out.push(`${s.runs}/${s.wickets}`)
  return out.filter(Boolean)
}

export default function Milestones() {
  const { id, at } = useMatchCtx()
  const [cat, setCat] = useState('all')
  const [all, setAll] = useState(false)
  const { data, loading, error, reload } = useApi(() => api.milestones(id, at, all), [id, at, all])
  if (loading && !data) return <Loading rows={3} />
  if (error) return <ErrorBox message={error} onRetry={reload} />
  const list = data.milestones.filter((m) => cat === 'all' || m.category === cat)
  const count = (c) => data.milestones.filter((m) => m.category === c).length

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-2">
        {CATS.map(([v, l]) => <button key={v} onClick={() => setCat(v)} className={`chip ${cat === v ? 'chip-on' : ''}`}>{l}{v !== 'all' ? ` (${count(v)})` : ` (${data.milestones.length})`}</button>)}
        <label className="ml-auto flex cursor-pointer items-center gap-2 text-xs text-mute">
          <input type="checkbox" checked={all} onChange={(e) => setAll(e.target.checked)} className="accent-[rgb(var(--accent))]" /> Include earlier steps (30s, 50s before a century…)
        </label>
      </div>

      {list.length === 0 ? <Empty title="No milestones yet">As the match goes on, 50s, 100s, wicket hauls, big stands and team landmarks will appear here.</Empty> : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {[...list].reverse().map((m) => {
            const st = STYLE[m.category]
            const Icon = st.icon
            return (
              <article key={m.id} className={`rounded-2xl border p-5 transition hover:-translate-y-0.5 ${st.bg} ${m.superseded ? 'opacity-70' : ''}`}>
                <div className="flex items-center gap-2">
                  <span className={`grid h-9 w-9 place-items-center rounded-xl bg-surface ${st.tone}`}><Icon size={18} /></span>
                  <span className={`font-display text-sm font-bold tracking-wide ${st.tone}`}>{m.badge}</span>
                  {m.match_fastest && <span className="ml-auto rounded-full bg-amber/20 px-2 py-0.5 text-[10px] font-bold text-amber">FASTEST IN MATCH</span>}
                </div>
                <h3 className="mt-3 font-display text-lg font-bold leading-snug">{m.title}</h3>
                <p className="mt-1.5 text-sm text-mute">{m.detail}</p>
                <div className="mt-3 flex flex-wrap gap-1.5">{chips(m).map((c) => <span key={c} className="num rounded-md bg-surface/70 px-2 py-1 text-[11px] font-semibold">{c}</span>)}</div>
                <div className="mt-3 text-xs text-mute">Innings {m.innings_no} · over {m.over} · {m.team}</div>
              </article>
            )
          })}
        </div>
      )}

      <section className="card-pad">
        <h3 className="mb-2 flex items-center gap-2 font-semibold"><Info size={16} className="text-sky" /> Not shown, on purpose</h3>
        <ul className="space-y-1.5 text-sm text-mute">{data.unavailable.map((u) => <li key={u.kind}>• {u.reason}</li>)}</ul>
      </section>
    </div>
  )
}
