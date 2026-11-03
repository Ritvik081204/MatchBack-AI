import { useMemo, useState } from 'react'
import { Award, ChevronDown, Flag, Flame, Pause, Play, Shield, TrendingUp, Tv, UserX, Zap, Sparkles, Cpu } from 'lucide-react'
import { Empty, ErrorBox, Loading, Spinner } from '../../components/ui'
import { useMatchCtx } from '../../lib/matchContext'
import { api, errorMessage } from '../../lib/api'
import { EVENT_META, colorBg, colorText } from '../../lib/format'
import { useApi } from '../../lib/hooks'

const ICONS = { wicket: UserX, six: Flame, four: Zap, milestone: Award, big_over: TrendingUp, maiden: Shield, drs: Tv, innings_break: Pause, innings_start: Play, phase: Flag }
const VIEWS = [['key', 'Key events'], ['all', 'Everything'], ['wicket', 'Wickets'], ['boundary', 'Boundaries'], ['milestone', 'Milestones'], ['turning', 'Turning points']]

function EventRow({ e, matchId, at, open, onToggle, explanation }) {
  const meta = EVENT_META[e.type] || EVENT_META.phase
  const Icon = ICONS[e.type] || Flag
  const tp = Boolean(e.turning_point)
  return (
    <li className={`rounded-2xl border transition ${tp ? 'border-accent/60 bg-accent/5' : 'border-line bg-surface'} ${open ? 'shadow-glow' : ''}`}>
      <button onClick={onToggle} aria-expanded={open} className="flex w-full items-start gap-3 p-3.5 text-left sm:p-4">
        <span className={`mt-0.5 grid h-9 w-9 shrink-0 place-items-center rounded-xl ${colorBg[meta.color]} ${colorText[meta.color]}`}><Icon size={17} /></span>
        <span className="min-w-0 flex-1">
          <span className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <span className="num rounded-md bg-surface2 px-1.5 py-0.5 text-[11px] font-bold">{e.over}</span>
            <span className="font-semibold">{e.title}</span>
            {tp && <span className="rounded-full bg-accent px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-accent-ink">Turning point</span>}
            {e.badge && <span className="rounded-full bg-amber/15 px-2 py-0.5 text-[10px] font-bold text-amber">{e.badge}</span>}
          </span>
          <span className="mt-1 block text-sm text-mute">{e.description}</span>
          <span className="num mt-1 block text-xs text-mute">{e.team} {e.score_after}</span>
        </span>
        <ChevronDown size={16} className={`mt-2 shrink-0 text-mute transition ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && (
        <div className="border-t border-line px-4 pb-4 pt-3 sm:pl-[4.25rem]">
          <div className="label mb-1.5 flex items-center gap-1.5 text-accent"><Sparkles size={12} /> Why it mattered</div>
          {!explanation && <div className="flex items-center gap-2 text-sm text-mute"><Spinner /> Working it out...</div>}
          {explanation?.error && <p className="text-sm text-rose">{explanation.error}</p>}
          {explanation?.explanation && (
            <>
              <p className="text-sm leading-relaxed">{explanation.explanation}</p>
              <div className="mt-2 flex flex-wrap items-center gap-3 text-[11px] text-mute">
                <span className="inline-flex items-center gap-1"><Cpu size={11} /> {explanation.engine === 'rule-based' ? 'Rule-based, from measured facts' : explanation.engine}</span>
                {explanation.facts?.innings_run_rate_before != null && <span>Innings run rate before: {explanation.facts.innings_run_rate_before}</span>}
                {explanation.facts?.runs_last_two_overs != null && <span>Last 2 overs: {explanation.facts.runs_last_two_overs} runs, {explanation.facts.wickets_last_two_overs} wkts</span>}
              </div>
            </>
          )}
        </div>
      )}
    </li>
  )
}

export default function Timeline() {
  const { id, at } = useMatchCtx()
  const { data, loading, error, reload } = useApi(() => api.timeline(id, at), [id, at])
  const [view, setView] = useState('key')
  const [inn, setInn] = useState('all')
  const [overSel, setOverSel] = useState(null)
  const [openId, setOpenId] = useState(null)
  const [explain, setExplain] = useState({})

  const stripInn = inn === 'all' ? data?.innings?.[data.innings.length - 1]?.innings_no : inn
  const events = useMemo(() => {
    if (!data) return []
    return data.events.filter((e) => {
      if (inn !== 'all' && e.innings_no !== inn) return false
      if (overSel && !(e.innings_no === overSel.innings_no && e.over_no === overSel.over)) return false
      if (view === 'key') return e.importance >= 40 || e.turning_point || e.type.startsWith('innings')
      if (view === 'turning') return Boolean(e.turning_point)
      if (view === 'all') return true
      return e.category === view
    })
  }, [data, view, inn, overSel])

  const groups = useMemo(() => {
    const g = []
    const idx = new Map()
    const overs = new Map((data?.overs || []).map((o) => [`${o.innings_no}-${o.over}`, o]))
    events.forEach((e) => {
      const k = `${e.innings_no}-${e.over_no}`
      if (!idx.has(k)) { idx.set(k, { key: k, innings_no: e.innings_no, over: e.over_no, team: e.team, summary: overs.get(k), events: [] }); g.push(idx.get(k)) }
      idx.get(k).events.push(e)
    })
    return g
  }, [events, data])

  const toggle = async (e) => {
    if (openId === e.id) return setOpenId(null)
    setOpenId(e.id)
    if (explain[e.id]) return
    try {
      const r = await api.explain(id, { event_id: e.id, at })
      setExplain((x) => ({ ...x, [e.id]: r }))
    } catch (err) { setExplain((x) => ({ ...x, [e.id]: { error: errorMessage(err) } })) }
  }

  if (loading && !data) return <Loading rows={4} />
  if (error) return <ErrorBox message={error} onRetry={reload} />
  const stripOvers = data.overs.filter((o) => o.innings_no === stripInn)
  const maxRuns = Math.max(8, ...stripOvers.map((o) => o.runs))
  const tpIds = new Set(data.turning_points.map((t) => t.id))

  return (
    <div className="space-y-5">
      <div className="card-pad space-y-4">
        <div className="flex flex-wrap items-center gap-2" role="tablist" aria-label="Event filter">
          {VIEWS.map(([v, l]) => (
            <button key={v} role="tab" aria-selected={view === v} onClick={() => setView(v)} className={`chip ${view === v ? 'chip-on' : ''}`}>
              {l}{v !== 'key' && v !== 'all' && v !== 'turning' ? ` (${data.counts[v] ?? 0})` : ''}{v === 'turning' ? ` (${data.turning_points.length})` : ''}
            </button>
          ))}
        </div>
        {data.innings.length > 1 && (
          <div className="flex flex-wrap items-center gap-2">
            <span className="label mr-1">Innings</span>
            <button onClick={() => { setInn('all'); setOverSel(null) }} className={`chip ${inn === 'all' ? 'chip-on' : ''}`}>All</button>
            {data.innings.map((i) => <button key={i.innings_no} onClick={() => { setInn(i.innings_no); setOverSel(null) }} className={`chip ${inn === i.innings_no ? 'chip-on' : ''}`}>{i.innings_no}. {i.team}</button>)}
          </div>
        )}
        <div>
          <div className="mb-2 flex items-center justify-between"><span className="label">Over by over{stripInn ? ` · innings ${stripInn}` : ''}</span>
            {overSel && <button onClick={() => setOverSel(null)} className="text-xs font-semibold text-accent">Clear over filter</button>}</div>
          <div className="scroll-x flex items-end gap-1.5 pb-1" role="listbox" aria-label="Overs">
            {stripOvers.map((o) => {
              const sel = overSel && overSel.over === o.over && overSel.innings_no === o.innings_no
              const hasTp = data.turning_points.some((t) => t.innings_no === o.innings_no && t.start_seq <= o.end_seq && t.end_seq >= o.start_seq)
              return (
                <button key={o.over} role="option" aria-selected={sel} onClick={() => { setOverSel(sel ? null : { innings_no: o.innings_no, over: o.over }); if (view === 'key') setView('all') }}
                  className={`group flex w-8 shrink-0 flex-col items-center gap-1 rounded-lg px-0.5 py-1 transition ${sel ? 'bg-accent/15' : 'hover:bg-surface2'}`} title={`Over ${o.over}: ${o.runs} runs, ${o.wickets} wkts`}>
                  <span className="num text-[10px] font-semibold">{o.runs}</span>
                  <span className={`w-5 rounded-t ${o.wickets ? 'bg-rose' : 'bg-accent/70'} ${hasTp ? 'ring-2 ring-amber' : ''}`} style={{ height: `${Math.max(4, (o.runs / maxRuns) * 56)}px` }} />
                  <span className="text-[10px] text-mute">{o.over}</span>
                </button>
              )
            })}
          </div>
          <p className="mt-1 text-[11px] text-mute">Red bars = wicket(s) fell. Amber ring = inside a turning point.</p>
        </div>
      </div>

      {groups.length === 0 ? (
        <Empty title="No events match this filter">Try "Everything" or clear the over filter.</Empty>
      ) : (
        <ol className="space-y-5">
          {groups.map((g, gi) => (
            <li key={g.key}>
              {(gi === 0 || groups[gi - 1].innings_no !== g.innings_no) && <div className="label mb-2 mt-2 text-accent">Innings {g.innings_no} · {g.team}</div>}
              <div className="mb-2 flex items-center gap-2 text-xs text-mute">
                <span className="font-semibold text-ink">Over {g.over}</span>
                {g.summary && <span className="num">{g.summary.runs} runs{g.summary.wickets ? `, ${g.summary.wickets} wkt${g.summary.wickets > 1 ? 's' : ''}` : ''} · {g.summary.cum_runs}/{g.summary.cum_wickets}</span>}
              </div>
              <ul className="space-y-2">
                {g.events.map((e) => <EventRow key={e.id} e={{ ...e, turning_point: e.turning_point && tpIds.has(e.turning_point) ? e.turning_point : null }}
                  matchId={id} at={at} open={openId === e.id} onToggle={() => toggle(e)} explanation={explain[e.id]} />)}
              </ul>
            </li>
          ))}
        </ol>
      )}
    </div>
  )
}
