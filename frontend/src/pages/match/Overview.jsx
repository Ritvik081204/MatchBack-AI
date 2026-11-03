import { Link, useNavigate, useOutletContext } from 'react-router-dom'
import { ArrowRight, Info, Sparkles, TrendingUp, User } from 'lucide-react'
import Highlights from '../../components/Highlights'
import { ErrorBox, Loading, Stat } from '../../components/ui'
import { api } from '../../lib/api'
import { useApi } from '../../lib/hooks'

export default function Overview() {
  const { match: m, id, at, search } = useOutletContext()
  const nav = useNavigate()
  const sit = m.situation
  const stats = useApi(() => api.statistics(id, at), [id, at])
  const tps = useApi(() => api.turningPoints(id, at), [id, at])
  const inProgress = !sit.completed
  const recent = (stats.data?.overs || []).filter((o) => o.innings_no === sit.innings_no).slice(-6)
  const maxRuns = Math.max(10, ...recent.map((o) => o.runs))
  const topTp = [...(tps.data?.turning_points || [])].sort((a, b) => a.rank - b.rank)[0]

  const lead = sit.lead
  const tiles = [
    ['Score', sit.score, `${sit.batting_team}`, true],
    ['Overs', sit.overs, m.format === 'TEST' ? `Innings ${sit.innings_no}` : null],
    ['Run rate', sit.run_rate ?? '-', 'runs per over'],
  ]
  if (sit.target && inProgress) tiles.push(['Target', sit.target, sit.runs_needed != null ? `${sit.runs_needed} more needed` : null])
  if (sit.required_rate && inProgress) tiles.push(['Required rate', sit.required_rate, sit.balls_remaining != null ? `${sit.balls_remaining} balls left` : null])
  if (lead != null && inProgress) tiles.push([lead >= 0 ? 'Lead' : 'Trail', Math.abs(lead), 'runs'])
  if (sit.projected && inProgress) tiles.push(['Projected', sit.projected, 'at current rate'])
  tiles.push(['Wickets lost', sit.wickets, `of 10`])

  return (
    <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
      <div className="space-y-6">
        <section className="card relative overflow-hidden p-5 sm:p-6">
          <div className="pitch-bg pointer-events-none absolute inset-0 opacity-60" aria-hidden="true" />
          <div className="relative flex flex-col gap-4 sm:flex-row sm:items-center">
            <div className="flex-1">
              <div className="label text-accent">Just joined?</div>
              <h2 className="mt-1 font-display text-2xl font-bold sm:text-3xl">Understand this match in 30 seconds</h2>
              <p className="mt-1.5 text-sm text-mute">One tap for a recap of everything that happened before you arrived{m.data_kind === 'DEMO' ? ' (as of the replay position)' : ''}.</p>
            </div>
            <button onClick={() => nav({ pathname: `/match/${id}/catch-up`, search }, { state: { auto: true } })} className="btn btn-primary !px-6 !py-3.5 text-base">
              <Sparkles size={18} /> Catch Me Up <ArrowRight size={16} />
            </button>
          </div>
        </section>

        <section className="card-pad">
          <div className="mb-4 flex items-center justify-between"><h3 className="font-display text-lg font-semibold">Match situation</h3>
            <span className="label">{inProgress ? 'as it stands' : 'final'}</span></div>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-4">
            {tiles.map(([l, v, s, a]) => <Stat key={l} label={l} value={v} sub={s} accent={a} />)}
          </div>
          <div className="mt-4 rounded-xl bg-surface2/70 p-3.5 text-sm"><span className="font-semibold">{sit.status}</span></div>

          {inProgress && !sit.innings_finished && (
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <div className="rounded-xl border border-line p-3.5">
                <div className="label mb-2">At the crease</div>
                {sit.current_batters.length ? sit.current_batters.map((b) => <div key={b} className="flex items-center gap-2 py-0.5 text-sm font-medium"><User size={13} className="text-accent" /> {b}</div>) : <span className="text-sm text-mute">-</span>}
                {sit.batter_note && <div className="mt-1 text-xs text-mute">{sit.batter_note}</div>}
              </div>
              <div className="rounded-xl border border-line p-3.5">
                <div className="label mb-2">Bowling now</div>
                <div className="text-sm font-medium">{sit.current_bowler || '-'}</div>
                <div className="mt-1 text-xs text-mute">Last ball: {sit.last_ball}</div>
              </div>
            </div>
          )}

          {sit.advantage && (
            <div className="mt-4 rounded-xl border border-amber/30 bg-amber/10 p-3.5 text-sm">
              <div className="font-semibold text-amber">Indicator: {sit.advantage.label}</div>
              <div className="mt-1 flex items-start gap-1.5 text-xs text-mute"><Info size={13} className="mt-0.5 shrink-0" /> A heuristic from the required vs current run rate and wickets lost. It is not a win probability.</div>
            </div>
          )}
        </section>

        {recent.length > 0 && (
          <section className="card-pad">
            <h3 className="mb-1 font-display text-lg font-semibold">Last {recent.length} overs</h3>
            <p className="mb-4 text-xs text-mute">{sit.batting_team} · runs per over (red = wicket fell)</p>
            <div className="flex h-36 items-end gap-2">
              {recent.map((o) => (
                <div key={o.over} className="flex flex-1 flex-col items-center gap-1">
                  <div className="num text-xs font-semibold">{o.runs}{o.wickets > 0 && <span className="ml-0.5 text-rose">W{o.wickets > 1 ? o.wickets : ''}</span>}</div>
                  <div className={`w-full rounded-t-md ${o.wickets ? 'bg-rose/70' : 'bg-accent/70'}`} style={{ height: `${Math.max(6, (o.runs / maxRuns) * 100)}px` }} />
                  <div className="text-[10px] text-mute">{o.over}</div>
                </div>
              ))}
            </div>
          </section>
        )}
      </div>

      <div className="space-y-6">
        <section className="card-pad">
          <h3 className="mb-4 font-display text-lg font-semibold">Standout performers</h3>
          {stats.loading && <Loading rows={2} />}
          {stats.error && <ErrorBox message={stats.error} onRetry={stats.reload} />}
          {stats.data && <Highlights highlights={stats.data.highlights} compact />}
          <Link to={{ pathname: `/match/${id}/players`, search }} className="mt-4 inline-flex items-center gap-1 text-sm font-semibold text-accent">All player insights <ArrowRight size={14} /></Link>
        </section>

        <section className="card-pad">
          <h3 className="mb-3 flex items-center gap-2 font-display text-lg font-semibold"><TrendingUp size={18} className="text-accent" /> Biggest turning point</h3>
          {tps.loading && <Loading rows={1} />}
          {tps.error && <ErrorBox message={tps.error} onRetry={tps.reload} />}
          {tps.data && !topTp && <p className="text-sm text-mute">No statistically significant turning point detected yet.</p>}
          {topTp && (
            <>
              <div className="mb-1 flex items-center gap-2 text-xs"><span className="rounded-full bg-accent/15 px-2 py-0.5 font-bold text-accent">{topTp.label}</span><span className="text-mute">{topTp.team} · overs {topTp.start_over}-{topTp.end_over}</span></div>
              <p className="text-sm leading-relaxed">{topTp.explanation}</p>
            </>
          )}
          <Link to={{ pathname: `/match/${id}/momentum`, search }} className="mt-4 inline-flex items-center gap-1 text-sm font-semibold text-accent">Momentum &amp; all turning points <ArrowRight size={14} /></Link>
        </section>

        <section className="card-pad">
          <h3 className="mb-3 font-display text-lg font-semibold">Innings so far</h3>
          <div className="space-y-2">
            {sit.innings_summary.map((i) => (
              <div key={i.innings_no} className="flex items-center justify-between rounded-xl bg-surface2/60 px-3.5 py-2.5 text-sm">
                <span className="font-medium">{i.innings_no}. {i.team}{i.declared ? ' (dec)' : ''}</span>
                <span className="num font-display font-bold">{i.runs}/{i.wickets} <span className="text-xs font-medium text-mute">({i.overs})</span></span>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  )
}
