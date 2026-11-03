import { useEffect, useMemo, useState } from 'react'
import { Link, NavLink, Outlet, useLocation, useParams, useSearchParams } from 'react-router-dom'
import { BarChart3, Calendar, ChevronLeft, Clock, LayoutDashboard, ListOrdered, MapPin, Rewind, Sparkles, TrendingUp, Trophy } from 'lucide-react'
import AskWidget from '../components/AskWidget'
import { DataBadge, ErrorBox, Loading, Notice, TeamBadge } from '../components/ui'
import { api, errorMessage } from '../lib/api'
import { FORMAT_LABEL, fmtDate } from '../lib/format'

const TABS = [
  { path: '', label: 'Overview', icon: LayoutDashboard, end: true },
  { path: 'catch-up', label: 'AI Catch-Up', icon: Sparkles },
  { path: 'timeline', label: 'Timeline', icon: Clock },
  { path: 'scorecard', label: 'Scorecard', icon: ListOrdered },
  { path: 'players', label: 'Player Insights', icon: BarChart3 },
  { path: 'milestones', label: 'Milestones', icon: Trophy },
  { path: 'momentum', label: 'Momentum', icon: TrendingUp },
]

function ReplayBar({ match, onCommit }) {
  const pts = match.replay.points
  const idxOf = (seq) => {
    let best = 0
    pts.forEach((p, i) => { if (p.seq <= seq) best = i })
    return best
  }
  const [idx, setIdx] = useState(idxOf(match.cutoff))
  useEffect(() => setIdx(idxOf(match.cutoff)), [match.cutoff]) // eslint-disable-line react-hooks/exhaustive-deps
  const p = pts[idx]
  const commit = () => onCommit(pts[idx].seq)
  return (
    <div className="rounded-2xl border border-violet/40 bg-violet/10 p-4">
      <div className="flex flex-wrap items-center gap-3">
        <Rewind size={16} className="text-violet" />
        <div className="text-sm font-semibold text-violet">Demo replay: choose when you "join" this match</div>
        <button className="chip ml-auto" onClick={() => { setIdx(idxOf(match.replay.default_seq)); onCommit(match.replay.default_seq) }}>Reset</button>
        <button className="chip" onClick={() => { setIdx(pts.length - 1); onCommit(pts[pts.length - 1].seq) }}>Jump to end</button>
      </div>
      <input type="range" min={0} max={pts.length - 1} value={idx} onChange={(e) => setIdx(+e.target.value)}
        onMouseUp={commit} onTouchEnd={commit} onKeyUp={(e) => ['ArrowLeft', 'ArrowRight', 'Home', 'End', 'PageUp', 'PageDown'].includes(e.key) && commit()}
        aria-label="Replay position" aria-valuetext={p.label} className="mt-3 w-full accent-[rgb(var(--violet))]" />
      <div className="mt-1 flex justify-between text-xs text-mute"><span>Start</span><span className="font-semibold text-violet">Now: {p.label} · {p.team} batting</span><span>End</span></div>
      <p className="mt-2 text-xs text-mute">Real ball-by-ball data replayed up to this point. Nothing after it is used in any summary, chart or answer.</p>
    </div>
  )
}

export default function MatchDetail() {
  const { id } = useParams()
  const [params, setParams] = useSearchParams()
  const location = useLocation()
  const atParam = params.get('at')
  const [state, setState] = useState({ match: null, loading: true, error: null })

  const load = useMemo(() => () => {
    let live = true
    api.match(id, atParam === null ? undefined : Number(atParam))
      .then((m) => live && setState({ match: m, loading: false, error: null }))
      .catch((e) => live && setState((s) => ({ match: s.match?.id === id ? s.match : null, loading: false, error: errorMessage(e) })))
    return () => { live = false }
  }, [id, atParam])

  useEffect(() => {
    setState((s) => ({ ...s, loading: s.match?.id !== id, error: null }))
    return load()
  }, [load, id])

  const setAt = (seq) => { const p = new URLSearchParams(params); p.set('at', String(seq)); setParams(p, { replace: true }) }

  if (state.loading && !state.match) return <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6"><Loading rows={3} label="Loading match" /></div>
  if (state.error && !state.match) {
    return <div className="mx-auto max-w-3xl px-4 py-10"><ErrorBox message={state.error} onRetry={load} /><Link to="/matches" className="btn btn-ghost mt-4"><ChevronLeft size={14} /> All matches</Link></div>
  }
  const m = state.match
  const sit = m.situation
  const isDemo = m.data_kind === 'DEMO'
  const search = location.search

  const teamBlock = (t, i) => {
    const sc = m.scores.filter((s) => s.team === t.name)
    const batting = sit.batting_team === t.name && !sit.completed
    return (
      <div className={`flex items-center gap-4 ${i === 1 ? 'md:flex-row-reverse md:text-right' : ''}`}>
        <TeamBadge team={t} size={56} />
        <div className="min-w-0">
          <div className="truncate font-display text-lg font-semibold sm:text-xl">{t.name}</div>
          {sc.length ? sc.map((s, k) => (
            <div key={k} className="num font-display text-2xl font-bold leading-tight sm:text-3xl">
              {s.score} <span className="text-sm font-medium text-mute">({s.overs} ov)</span>
            </div>
          )) : <div className="text-sm text-mute">Yet to bat</div>}
          {batting && <div className="mt-1 text-[11px] font-semibold uppercase tracking-wider text-accent">Batting</div>}
        </div>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-7xl px-4 pb-10 pt-6 sm:px-6">
      <Link to="/matches" className="mb-4 inline-flex items-center gap-1 text-sm text-mute hover:text-ink"><ChevronLeft size={14} /> All matches</Link>

      <section className="card relative overflow-hidden p-5 sm:p-7">
        <div className="pitch-bg pointer-events-none absolute inset-0 opacity-70" aria-hidden="true" />
        <div className="relative">
          <div className="flex flex-wrap items-center gap-2">
            <DataBadge kind={m.data_kind} />
            <span className="rounded-full bg-surface2 px-2.5 py-1 text-[11px] font-bold">{FORMAT_LABEL[m.format]}</span>
            {m.gender === 'female' && <span className="rounded-full bg-surface2 px-2.5 py-1 text-[11px] font-semibold text-mute">Women</span>}
            <span className="text-xs text-mute">{m.tournament}{m.stage ? ` · ${m.stage}` : ''}{m.season ? ` · ${m.season}` : ''}</span>
          </div>

          <div className="mt-5 grid gap-5 md:grid-cols-[1fr_auto_1fr] md:items-center">
            {teamBlock(m.teams[0], 0)}
            <div className="hidden font-display text-sm font-bold text-mute md:block">VS</div>
            {teamBlock(m.teams[1], 1)}
          </div>

          <div className={`mt-5 rounded-xl px-4 py-3 text-sm font-semibold sm:text-base ${isDemo ? 'bg-violet/15 text-violet' : 'bg-accent/10 text-accent'}`}>
            {m.status_text}
          </div>
          <div className="mt-3 flex flex-wrap gap-x-5 gap-y-1 text-xs text-mute">
            <span className="inline-flex items-center gap-1"><Calendar size={12} /> {fmtDate(m.date)}</span>
            {m.venue && <span className="inline-flex items-center gap-1"><MapPin size={12} /> {m.venue}{m.city ? `, ${m.city}` : ''}</span>}
            {m.toss?.winner && <span>Toss: {m.toss.winner} chose to {m.toss.decision}</span>}
          </div>
        </div>
      </section>

      {isDemo && (
        <div className="mt-4 space-y-3">
          <Notice tone="demo"><b>DEMO MATCH.</b> {m.label.replace('DEMO MATCH - ', '')}</Notice>
          {m.replay && <ReplayBar match={m} onCommit={setAt} />}
        </div>
      )}
      {m.data_issues?.length > 0 && <Notice tone="warn" className="mt-4">Data notes: {m.data_issues.join('; ')}.</Notice>}

      <nav className="scroll-x sticky top-16 z-30 -mx-4 mt-6 border-b border-line bg-bg/85 px-4 backdrop-blur-xl sm:mx-0 sm:rounded-2xl sm:border sm:px-2" aria-label="Match sections">
        <div className="flex min-w-max gap-1 py-1.5">
          {TABS.map((t) => (
            <NavLink key={t.path} to={{ pathname: `/match/${id}${t.path ? '/' + t.path : ''}`, search }} end={t.end}
              className={({ isActive }) => `inline-flex items-center gap-2 whitespace-nowrap rounded-xl px-3.5 py-2 text-sm font-semibold transition ${isActive ? 'bg-accent text-accent-ink' : 'text-mute hover:bg-surface2 hover:text-ink'}`}>
              <t.icon size={15} /> {t.label}
            </NavLink>
          ))}
        </div>
      </nav>

      <div className="mt-6 animate-rise" key={`${location.pathname}`}>
        <Outlet context={{ match: m, id, at: m.cutoff, search, reloadMatch: load }} />
      </div>

      <AskWidget matchId={id} at={m.cutoff} match={m} />
    </div>
  )
}
