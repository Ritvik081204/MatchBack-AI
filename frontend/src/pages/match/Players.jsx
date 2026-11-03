import { useMemo, useState } from 'react'
import { Bar, BarChart, CartesianGrid, Cell, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Info } from 'lucide-react'
import Highlights from '../../components/Highlights'
import { Empty, ErrorBox, Loading } from '../../components/ui'
import { useMatchCtx } from '../../lib/matchContext'
import { api } from '../../lib/api'
import { useApi } from '../../lib/hooks'
import { useChartColors } from '../../lib/theme'

const INDICATOR = {
  outstanding: 'bg-accent text-accent-ink', strong: 'bg-accent/20 text-accent', steady: 'bg-sky/15 text-sky', limited: 'bg-surface2 text-mute',
}

function ChartCard({ title, sub, children, empty }) {
  return (
    <section className="card-pad">
      <h3 className="font-display text-base font-semibold">{title}</h3>
      {sub && <p className="mb-3 text-xs text-mute">{sub}</p>}
      {empty ? <p className="py-10 text-center text-sm text-mute">{empty}</p> : <div className="h-72 w-full">{children}</div>}
    </section>
  )
}

function PartnershipTip({ active, payload }) {
  if (!active || !payload?.length) return null
  const r = payload[0].payload
  return (
    <div className="rounded-xl border border-line bg-surface p-3 text-xs shadow-xl">
      <div className="mb-1 font-semibold">{r.label}</div>
      <div>{r.n1}: <b>{r.p1}</b></div><div>{r.n2}: <b>{r.p2}</b></div>
      <div className="mt-1 text-mute">Extras &amp; others: {r.rest} · total {r.runs} off {r.balls} balls{r.unbroken ? ' (unbroken)' : ''}</div>
    </div>
  )
}

export default function Players() {
  const { id, at, match } = useMatchCtx()
  const { data, loading, error, reload } = useApi(() => api.statistics(id, at), [id, at])
  const col = useChartColors()
  const [team, setTeam] = useState('all')
  const [sort, setSort] = useState('impact')
  const [showAll, setShowAll] = useState(false)
  const [inn, setInn] = useState(null)
  const [who, setWho] = useState('')

  const teamColor = useMemo(() => ({ [match.teams[0].name]: col.accent, [match.teams[1].name]: col.sky }), [match, col.accent, col.sky])
  const players = data?.players || []

  const sorted = useMemo(() => {
    const f = players.filter((p) => team === 'all' || p.team === team)
    const key = { impact: (p) => p.impact, runs: (p) => p.batting?.runs ?? -1, wickets: (p) => p.bowling?.wickets ?? -1 }[sort]
    return [...f].sort((a, b) => key(b) - key(a))
  }, [players, team, sort])

  if (loading && !data) return <Loading rows={4} />
  if (error) return <ErrorBox message={error} onRetry={reload} />
  if (!players.length) return <Empty title="No player data yet">Once the match is underway, player insights will appear here.</Empty>

  const batters = players.filter((p) => p.batting?.balls > 0).sort((a, b) => b.batting.runs - a.batting.runs).slice(0, 10)
    .map((p) => ({ name: p.name, runs: p.batting.runs, balls: p.batting.balls, team: p.team, sr: p.batting.strike_rate }))
  const bowlers = players.filter((p) => p.bowling?.wickets > 0).sort((a, b) => b.bowling.wickets - a.bowling.wickets || a.bowling.runs - b.bowling.runs).slice(0, 8)
    .map((p) => ({ name: p.name, wickets: p.bowling.wickets, runs: p.bowling.runs, team: p.team }))
  const inningsList = [...new Set(data.overs.map((o) => o.innings_no))]
  const curInn = inn ?? inningsList[inningsList.length - 1]
  const overs = data.overs.filter((o) => o.innings_no === curInn).map((o) => ({ over: o.over, runs: o.runs, wickets: o.wickets, team: o.team }))
  const parts = [...data.partnerships].sort((a, b) => b.runs - a.runs).slice(0, 8).map((p) => {
    const [n1, n2] = p.batters
    const p1 = p.contributions[n1]?.runs ?? 0
    const p2 = n2 ? p.contributions[n2]?.runs ?? 0 : 0
    return { label: `${p.batters.join(' & ')} (inn ${p.innings_no}, wkt ${p.wicket_no})`, short: p.batters.map((b) => b.split(' ').pop()).join(' & '), n1, n2: n2 || '-', p1, p2,
      rest: Math.max(0, p.runs - p1 - p2), runs: p.runs, balls: p.balls, unbroken: p.unbroken }
  })
  const focus = players.find((p) => p.name === who) || sorted[0]
  const bt = focus?.batting
  const split = bt ? [
    { k: 'In boundaries', v: bt.fours * 4 + bt.sixes * 6, c: col.accent },
    { k: 'Running / other', v: Math.max(0, bt.runs - bt.fours * 4 - bt.sixes * 6), c: col.sky },
  ] : []
  const axis = { stroke: col.line }

  return (
    <div className="space-y-6">
      <section className="card-pad"><h3 className="mb-4 font-display text-lg font-semibold">Standout performances</h3><Highlights highlights={data.highlights} /></section>

      <div className="grid gap-4 lg:grid-cols-2">
        <ChartCard title="Runs by batter" sub="Top run-scorers (labels show runs)" empty={!batters.length && 'No batting yet.'}>
          <ResponsiveContainer><BarChart data={batters} layout="vertical" margin={{ left: 8, right: 36 }}>
            <CartesianGrid stroke={col.line} strokeDasharray="3 3" horizontal={false} />
            <XAxis type="number" {...axis} /><YAxis type="category" dataKey="name" width={110} tick={{ fontSize: 11 }} {...axis} />
            <Tooltip cursor={{ fill: col.line, opacity: 0.3 }} formatter={(v, n, p) => [`${v} off ${p.payload.balls} (SR ${p.payload.sr})`, p.payload.team]} />
            <Bar isAnimationActive={false} dataKey="runs" radius={[0, 6, 6, 0]}>{batters.map((b) => <Cell key={b.name} fill={teamColor[b.team] || col.accent} />)}<LabelList dataKey="runs" position="right" fill={col.ink} fontSize={11} /></Bar>
          </BarChart></ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Wickets by bowler" sub="Wickets credited to the bowler (run-outs excluded)" empty={!bowlers.length && 'No bowler has taken a wicket yet.'}>
          <ResponsiveContainer><BarChart data={bowlers} layout="vertical" margin={{ left: 8, right: 36 }}>
            <CartesianGrid stroke={col.line} strokeDasharray="3 3" horizontal={false} />
            <XAxis type="number" allowDecimals={false} {...axis} /><YAxis type="category" dataKey="name" width={110} tick={{ fontSize: 11 }} {...axis} />
            <Tooltip cursor={{ fill: col.line, opacity: 0.3 }} formatter={(v, n, p) => [`${v} for ${p.payload.runs}`, p.payload.team]} />
            <Bar isAnimationActive={false} dataKey="wickets" radius={[0, 6, 6, 0]}>{bowlers.map((b) => <Cell key={b.name} fill={teamColor[b.team] || col.accent} />)}<LabelList dataKey="wickets" position="right" fill={col.ink} fontSize={11} /></Bar>
          </BarChart></ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Over-by-over scoring" sub={`Innings ${curInn} · red = a wicket fell in the over`}>
          <div className="mb-2 flex flex-wrap gap-1.5">
            {inningsList.map((n) => <button key={n} onClick={() => setInn(n)} className={`chip !py-1 ${curInn === n ? 'chip-on' : ''}`}>Innings {n}</button>)}
          </div>
          <ResponsiveContainer height="88%"><BarChart data={overs}>
            <CartesianGrid stroke={col.line} strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="over" {...axis} interval="preserveStartEnd" /><YAxis allowDecimals={false} {...axis} />
            <Tooltip cursor={{ fill: col.line, opacity: 0.3 }} formatter={(v, n, p) => [`${v} runs${p.payload.wickets ? `, ${p.payload.wickets} wkt` : ''}`, `Over ${p.payload.over}`]} />
            <Bar isAnimationActive={false} dataKey="runs" radius={[4, 4, 0, 0]}>{overs.map((o) => <Cell key={o.over} fill={o.wickets ? col.rose : (teamColor[o.team] || col.accent)} />)}</Bar>
          </BarChart></ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Partnership comparison" sub="Biggest partnerships, split by batter (remainder = extras)" empty={!parts.length && 'No partnerships yet.'}>
          <ResponsiveContainer><BarChart data={parts} layout="vertical" margin={{ left: 8, right: 20 }}>
            <CartesianGrid stroke={col.line} strokeDasharray="3 3" horizontal={false} />
            <XAxis type="number" {...axis} /><YAxis type="category" dataKey="short" width={110} tick={{ fontSize: 10 }} {...axis} />
            <Tooltip content={<PartnershipTip />} cursor={{ fill: col.line, opacity: 0.3 }} />
            <Bar isAnimationActive={false} dataKey="p1" stackId="a" fill={col.accent} /><Bar isAnimationActive={false} dataKey="p2" stackId="a" fill={col.sky} /><Bar isAnimationActive={false} dataKey="rest" stackId="a" fill={col.mute} radius={[0, 6, 6, 0]} />
          </BarChart></ResponsiveContainer>
        </ChartCard>
      </div>

      {focus && (
        <section className="card-pad">
          <div className="mb-4 flex flex-wrap items-center gap-3">
            <h3 className="font-display text-base font-semibold">Individual performance</h3>
            <select value={focus.name} onChange={(e) => setWho(e.target.value)} aria-label="Choose a player" className="ml-auto rounded-xl border border-line bg-surface2 px-3 py-2 text-sm outline-none focus:border-accent">
              {players.map((p) => <option key={p.name} value={p.name}>{p.name} ({p.team})</option>)}
            </select>
          </div>
          <div className="grid gap-6 md:grid-cols-2">
            <div>
              <div className="font-semibold">{focus.name} <span className="text-sm font-normal text-mute">· {focus.team} · {focus.observed_role} (observed)</span></div>
              <p className="mt-2 text-sm leading-relaxed text-mute">{focus.insight || 'No batting, bowling or fielding recorded yet.'}</p>
              <dl className="mt-3 grid grid-cols-3 gap-2 text-center text-xs">
                {bt && [['Runs', bt.runs], ['Balls', bt.balls], ['SR', bt.strike_rate ?? '-']].map(([k, v]) => <div key={k} className="rounded-lg bg-surface2/60 p-2"><dt className="text-mute">{k}</dt><dd className="num font-display text-lg font-bold">{v}</dd></div>)}
                {focus.bowling && [['Wkts', focus.bowling.wickets], ['Runs', focus.bowling.runs], ['Econ', focus.bowling.economy ?? '-']].map(([k, v]) => <div key={'b' + k} className="rounded-lg bg-surface2/60 p-2"><dt className="text-mute">Bowl {k}</dt><dd className="num font-display text-lg font-bold">{v}</dd></div>)}
              </dl>
            </div>
            <div className="h-44">
              {bt?.runs > 0 ? (
                <ResponsiveContainer><BarChart data={split} layout="vertical" margin={{ left: 8, right: 30 }}>
                  <XAxis type="number" hide /><YAxis type="category" dataKey="k" width={110} tick={{ fontSize: 11 }} {...axis} />
                  <Tooltip cursor={false} formatter={(v) => [`${v} runs`]} />
                  <Bar isAnimationActive={false} dataKey="v" radius={[0, 6, 6, 0]}>{split.map((s) => <Cell key={s.k} fill={s.c} />)}<LabelList dataKey="v" position="right" fill={col.ink} fontSize={11} /></Bar>
                </BarChart></ResponsiveContainer>
              ) : <p className="grid h-full place-items-center text-sm text-mute">No runs to break down.</p>}
            </div>
          </div>
        </section>
      )}

      <section>
        <div className="mb-4 flex flex-wrap items-center gap-2">
          <h3 className="mr-auto font-display text-lg font-semibold">Player cards</h3>
          <button onClick={() => setTeam('all')} className={`chip ${team === 'all' ? 'chip-on' : ''}`}>Both teams</button>
          {match.teams.map((t) => <button key={t.name} onClick={() => setTeam(t.name)} className={`chip ${team === t.name ? 'chip-on' : ''}`}>{t.name}</button>)}
          <select value={sort} onChange={(e) => setSort(e.target.value)} aria-label="Sort players" className="rounded-xl border border-line bg-surface2 px-3 py-1.5 text-xs outline-none focus:border-accent">
            <option value="impact">Sort: contribution</option><option value="runs">Sort: runs</option><option value="wickets">Sort: wickets</option>
          </select>
        </div>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {sorted.slice(0, showAll ? 100 : 9).map((p) => (
            <article key={p.name} className="card-pad flex flex-col gap-3">
              <div className="flex items-start gap-3">
                <div className="min-w-0 flex-1">
                  <div className="truncate font-semibold">{p.name}{p.is_player_of_match && <span className="ml-2 rounded-full bg-amber/15 px-2 py-0.5 text-[10px] font-bold text-amber">POTM</span>}</div>
                  <div className="text-xs text-mute">{p.team} · {p.observed_role}</div>
                </div>
                <span className={`rounded-full px-2.5 py-1 text-[11px] font-bold capitalize ${INDICATOR[p.indicator]}`} title="Derived from the custom contribution score">{p.indicator}</span>
              </div>
              <div className="grid grid-cols-3 gap-2 text-center text-xs">
                {p.batting?.balls > 0 && <div className="rounded-lg bg-surface2/60 p-2"><div className="text-mute">Bat</div><div className="num font-display text-base font-bold">{p.batting.runs}<span className="text-xs font-medium text-mute"> ({p.batting.balls})</span></div></div>}
                {p.bowling?.legal_balls > 0 && <div className="rounded-lg bg-surface2/60 p-2"><div className="text-mute">Bowl</div><div className="num font-display text-base font-bold">{p.bowling.wickets}/{p.bowling.runs}</div></div>}
                <div className="rounded-lg bg-surface2/60 p-2"><div className="text-mute">Points</div><div className="num font-display text-base font-bold text-accent">{p.impact}</div></div>
              </div>
              <p className="text-sm leading-relaxed text-mute">{p.insight}</p>
            </article>
          ))}
        </div>
        {sorted.length > 9 && <div className="mt-5 text-center"><button className="btn btn-ghost" onClick={() => setShowAll((s) => !s)}>{showAll ? 'Show fewer' : `Show all ${sorted.length} players`}</button></div>}
      </section>

      <details className="card-pad group">
        <summary className="flex cursor-pointer list-none items-center gap-2 font-semibold"><Info size={16} className="text-sky" /> How these numbers are derived &amp; their limits</summary>
        <ul className="mt-3 list-disc space-y-1.5 pl-5 text-sm text-mute">{data.limitations.map((l) => <li key={l}>{l}</li>)}</ul>
      </details>
    </div>
  )
}
