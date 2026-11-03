import { lazy, Suspense } from 'react'
import { Award, Flame, UserX, Zap } from 'lucide-react'
import { Loading } from './ui'
import { MatchCtx } from '../lib/matchContext'

const CatchUp = lazy(() => import('../pages/match/CatchUp'))
const Timeline = lazy(() => import('../pages/match/Timeline'))
const Scorecard = lazy(() => import('../pages/match/Scorecard'))
const Players = lazy(() => import('../pages/match/Players'))
const Milestones = lazy(() => import('../pages/match/Milestones'))
const Momentum = lazy(() => import('../pages/match/Momentum'))

export const TABS = [['live', 'Live'], ['catchup', 'Catch Up'], ['timeline', 'Timeline'], ['scorecard', 'Scorecard'], ['players', 'Players'], ['milestones', 'Milestones'], ['momentum', 'Momentum']]
export const TOAST_ICON = { wicket: UserX, six: Flame, four: Zap, milestone: Award, big_over: Flame, innings_break: Award }
export const TOAST_TONE = { wicket: 'border-rose', six: 'border-accent', four: 'border-sky', milestone: 'border-amber', big_over: 'border-accent', innings_break: 'border-sky' }

export function BallBubble({ b }) {
  let txt = b.total === 0 ? '•' : String(b.total); let cls = 'bg-surface2 text-mute'
  if (b.is_wicket) { txt = 'W'; cls = 'bg-rose text-white' } else if (b.is_six) { txt = '6'; cls = 'bg-accent text-accent-ink' } else if (b.is_four) { txt = '4'; cls = 'bg-sky text-white' }
  else if (!b.legal) { txt = b.batter_runs === 0 && b.extras > 0 ? 'Wd' : 'Nb'; cls = 'bg-amber/20 text-amber' }
  return <span className={`grid h-8 w-8 shrink-0 place-items-center rounded-full text-xs font-bold ${cls}`}>{txt}</span>
}

export function TabNav({ tab, onOpen, top = 'top-14' }) {
  return (
    <nav className={`scroll-x sticky ${top} z-30 mt-3 border-b border-line bg-bg/95 px-4 backdrop-blur sm:px-0`} aria-label="Insights">
      <div className="flex min-w-max gap-1 py-1.5">
        {TABS.map(([k, l]) => (
          <button key={k} onClick={() => onOpen(k)} aria-current={tab === k} className={`rounded-xl px-3.5 py-2 text-sm font-semibold transition ${tab === k ? 'bg-accent text-accent-ink' : 'text-mute hover:bg-surface2 hover:text-ink'}`}>{l}</button>
        ))}
      </div>
    </nav>
  )
}

/** The "Live" panel (this over, latest moments) or one of the embedded insight tabs. */
export function TabBody({ tab, ctx, tick, cur, overBalls, feed, onOpen }) {
  if (tab === 'live') {
    return (
      <div className="space-y-4">
        <section className="card-pad">
          <div className="mb-3 flex items-center justify-between"><h3 className="font-display text-base font-semibold">This over</h3><span className="text-xs text-mute">Over {cur.over_no + 1} · {cur.bowler}</span></div>
          <div className="scroll-x flex gap-2">{overBalls.map((b) => <BallBubble key={b.seq} b={b} />)}</div>
          <div className="mt-3 grid grid-cols-3 gap-2 text-center">
            {[['Score', tick.score], ['Run rate', tick.rr], [tick.rrr ? 'Required' : 'Overs', tick.rrr || tick.overs]].map(([k, v]) => (
              <div key={k} className="rounded-xl bg-surface2 p-2.5"><div className="label">{k}</div><div className="num font-display text-lg font-bold">{v}</div></div>
            ))}
          </div>
          <div className="mt-3 text-xs text-mute">At the crease: <b className="text-ink">{cur.batter}</b>{cur.non_striker ? ` & ${cur.non_striker}` : ''}</div>
        </section>
        <section className="card-pad">
          <h3 className="mb-3 font-display text-base font-semibold">Latest moments</h3>
          {feed.length === 0 ? <p className="text-sm text-mute">Nothing big yet.</p> : (
            <ul className="space-y-2.5">{feed.map((e) => <li key={e.id} className="flex gap-3 text-sm"><span className="num w-10 shrink-0 text-xs font-bold text-mute">{e.over}</span><div><div className="font-semibold">{e.title}</div><div className="text-xs text-mute">{e.description}</div></div></li>)}</ul>
          )}
          <button onClick={() => onOpen('timeline')} className="mt-3 text-sm font-semibold text-accent">Full timeline →</button>
        </section>
      </div>
    )
  }
  if (!ctx) return <Loading rows={3} />
  return (
    <MatchCtx.Provider value={ctx}>
      <Suspense fallback={<Loading rows={3} />}>
        {tab === 'catchup' && <CatchUp />}
        {tab === 'timeline' && <Timeline />}
        {tab === 'scorecard' && <Scorecard />}
        {tab === 'players' && <Players />}
        {tab === 'milestones' && <Milestones />}
        {tab === 'momentum' && <Momentum />}
      </Suspense>
    </MatchCtx.Provider>
  )
}
