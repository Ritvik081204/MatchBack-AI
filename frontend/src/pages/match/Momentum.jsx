import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Area, AreaChart, Bar, CartesianGrid, Cell, ComposedChart, Legend, Line, ReferenceArea, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Info, TrendingUp } from 'lucide-react'
import { Empty, ErrorBox, Loading, Notice } from '../../components/ui'
import { useMatchCtx } from '../../lib/matchContext'
import { api } from '../../lib/api'
import { useApi } from '../../lib/hooks'
import { useChartColors } from '../../lib/theme'

const overOf = (label) => Number(String(label).split('.')[0]) + 1

export default function Momentum() {
  const { id, at, search, embedded } = useMatchCtx()
  const { data, loading, error, reload } = useApi(() => api.turningPoints(id, at), [id, at])
  const col = useChartColors()
  const [inn, setInn] = useState(null)
  const [hover, setHover] = useState(null)
  if (loading && !data) return <Loading rows={3} />
  if (error) return <ErrorBox message={error} onRetry={reload} />
  if (!data.momentum.length) return <Empty title="Not enough play yet">Momentum appears once overs have been bowled.</Empty>

  const n = inn ?? data.innings[data.innings.length - 1].innings_no
  const series = data.momentum.filter((r) => r.innings_no === n)
  const tps = [...data.turning_points].sort((a, b) => a.rank - b.rank)
  const tpHere = tps.filter((t) => t.innings_no === n)
  const hasReq = series.some((r) => r.required_rate != null)
  const axis = { stroke: col.line }
  const wicketDot = (p) => (p.payload.wickets ? <circle key={p.key} cx={p.cx} cy={p.cy} r={5} fill={col.rose} stroke={col.surface} strokeWidth={2} /> : <g key={p.key} />)

  return (
    <div className="space-y-6">
      <Notice tone="warn">
        <b>Derived indicator, not a win probability.</b> {data.disclaimer}
      </Notice>

      <div className="flex flex-wrap gap-2">
        {data.innings.map((i) => <button key={i.innings_no} onClick={() => setInn(i.innings_no)} className={`chip ${n === i.innings_no ? 'chip-on' : ''}`}>Innings {i.innings_no} · {i.team}</button>)}
      </div>

      <section className="card-pad">
        <h3 className="font-display text-base font-semibold">Runs per over{hasReq ? ' and required rate' : ''}</h3>
        <p className="mb-3 text-xs text-mute">Red bars = wicket(s). Shaded bands = detected turning points (hover a card below to highlight).</p>
        <div className="h-80">
          <ResponsiveContainer><ComposedChart data={series} margin={{ right: 10 }}>
            <CartesianGrid stroke={col.line} strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="over" {...axis} /><YAxis allowDecimals={false} {...axis} />
            {tpHere.map((t) => <ReferenceArea key={t.id} x1={overOf(t.start_over)} x2={overOf(t.end_over)} fill={col.amber} fillOpacity={hover === t.id ? 0.35 : 0.12} stroke={col.amber} strokeOpacity={hover === t.id ? 0.9 : 0.3} />)}
            <Tooltip cursor={{ fill: col.line, opacity: 0.25 }} formatter={(v, name) => [v, name]} labelFormatter={(o) => `Over ${o}`} />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            <Bar isAnimationActive={false} dataKey="runs" name="Runs in over" fill={col.accent} radius={[4, 4, 0, 0]}>{series.map((r) => <Cell key={r.over} fill={r.wickets ? col.rose : col.accent} />)}</Bar>
            {hasReq && <Line isAnimationActive={false} type="monotone" dataKey="required_rate" name="Required rate" stroke={col.amber} strokeWidth={2} dot={false} connectNulls />}
          </ComposedChart></ResponsiveContainer>
        </div>
      </section>

      <div className="grid gap-4 lg:grid-cols-2">
        <section className="card-pad">
          <h3 className="font-display text-base font-semibold">Cumulative score</h3>
          <p className="mb-3 text-xs text-mute">Red dots mark overs in which a wicket fell.</p>
          <div className="h-64">
            <ResponsiveContainer><ComposedChart data={series}>
              <CartesianGrid stroke={col.line} strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="over" {...axis} /><YAxis {...axis} />
              <Tooltip labelFormatter={(o) => `Over ${o}`} formatter={(v, name, p) => [`${v}/${p.payload.cum_wickets}`, 'Score']} />
              <Line isAnimationActive={false} type="monotone" dataKey="cum_runs" name="Score" stroke={col.sky} strokeWidth={2.5} dot={wicketDot} activeDot={{ r: 5 }} />
            </ComposedChart></ResponsiveContainer>
          </div>
        </section>

        <section className="card-pad">
          <h3 className="font-display text-base font-semibold">Momentum indicator</h3>
          <p className="mb-3 text-xs text-mute">Recent scoring vs the innings trend, minus a penalty for wickets in the window. Above 0 favours the batting side.</p>
          <div className="h-64">
            <ResponsiveContainer><AreaChart data={series}>
              <defs><linearGradient id="mom" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={col.accent} stopOpacity={0.55} /><stop offset="100%" stopColor={col.accent} stopOpacity={0.05} /></linearGradient></defs>
              <CartesianGrid stroke={col.line} strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="over" {...axis} /><YAxis domain={[-100, 100]} {...axis} />
              <ReferenceLine y={0} stroke={col.mute} strokeDasharray="4 4" />
              <Tooltip labelFormatter={(o) => `Over ${o}`} formatter={(v) => [v, 'Momentum index']} />
              <Area isAnimationActive={false} type="monotone" dataKey="momentum" stroke={col.accent} strokeWidth={2} fill="url(#mom)" />
            </AreaChart></ResponsiveContainer>
          </div>
        </section>
      </div>

      <section>
        <h3 className="mb-1 flex items-center gap-2 font-display text-lg font-semibold"><TrendingUp size={18} className="text-accent" /> Turning points, ranked</h3>
        <p className="mb-4 text-sm text-mute">Not every wicket is a turning point: moments are scored from measured indicators (wickets in a window, partnership size, run-rate gap, scoring swings) and only the strongest, non-overlapping ones are kept.</p>
        {tps.length === 0 ? <Empty title="No turning points detected">Nothing has crossed the detection thresholds so far.</Empty> : (
          <ol className="grid gap-3 md:grid-cols-2">
            {tps.map((t) => (
              <li key={t.id} onMouseEnter={() => { setHover(t.id); setInn(t.innings_no) }} onMouseLeave={() => setHover(null)} className="card-pad transition hover:border-accent/60">
                <div className="flex items-center gap-2">
                  <span className="grid h-7 w-7 place-items-center rounded-lg bg-accent text-sm font-bold text-accent-ink">{t.rank}</span>
                  <span className="font-semibold">{t.label}</span>
                  <span className="ml-auto text-xs text-mute">{t.team} · {t.start_over}–{t.end_over}</span>
                </div>
                <div className="mt-3 flex items-center gap-2" title="Score 0-100 from measured indicators">
                  <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-surface2"><div className="h-full rounded-full bg-accent" style={{ width: `${t.score}%` }} /></div>
                  <span className="num text-xs font-bold">{t.score}</span>
                </div>
                <p className="mt-3 text-sm leading-relaxed text-mute">{t.explanation}</p>
                {!embedded && <Link to={{ pathname: `/match/${id}/timeline`, search }} className="mt-3 inline-block text-xs font-semibold text-accent">See in timeline →</Link>}
              </li>
            ))}
          </ol>
        )}
      </section>

      <details className="card-pad">
        <summary className="flex cursor-pointer list-none items-center gap-2 font-semibold"><Info size={16} className="text-sky" /> Detection rules for this format</summary>
        <div className="mt-3 grid grid-cols-2 gap-2 text-xs sm:grid-cols-3">
          {Object.entries(data.config).map(([k, v]) => <div key={k} className="rounded-lg bg-surface2/60 p-2"><div className="text-mute">{k.replace(/_/g, ' ')}</div><div className="num font-bold">{String(v)}</div></div>)}
        </div>
      </details>
    </div>
  )
}
