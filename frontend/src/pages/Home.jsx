import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ArrowRight, Award, BarChart3, Bot, Clock, MessageCircle, MousePointerClick, Search, Sparkles, TrendingUp, Zap } from 'lucide-react'
import HeroBackground from '../components/HeroBackground'
import MatchCard from '../components/MatchCard'
import { DataBadge, Empty, ErrorBox, Loading, Notice, SectionTitle, TeamBadge } from '../components/ui'
import { api } from '../lib/api'
import { useApi } from '../lib/hooks'

const CATEGORIES = [
  { id: 'live', label: 'Live Matches' },
  { id: 'upcoming', label: 'Upcoming' },
  { id: 'recent', label: 'Recent' },
  { id: 'completed', label: 'Completed' },
]

function FeaturedMatch({ match }) {
  const nav = useNavigate()
  const recap = useApi(() => api.catchUp(match.id, { length: 'quick', focus: 'everything', at: match.default_cutoff }), [match.id])
  return (
    <div className="card relative overflow-hidden p-5 shadow-glow sm:p-6">
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <DataBadge kind="DEMO" />
        <span className="text-xs text-mute">Replay of a real match · not live</span>
      </div>
      <div className="space-y-3">
        {match.teams.map((t) => {
          const sc = match.scores.filter((s) => s.team === t.name)
          return (
            <div key={t.name} className="flex items-center gap-3">
              <TeamBadge team={t} size={44} />
              <div className="flex-1 font-display text-lg font-semibold">{t.name}</div>
              <div className="num text-right font-display text-xl font-bold">
                {sc.length ? sc.map((s, i) => <div key={i}>{s.score} <span className="text-xs font-medium text-mute">({s.overs})</span></div>) : <span className="text-sm text-mute">yet to bat</span>}
              </div>
            </div>
          )
        })}
      </div>
      <div className="mt-4 rounded-xl bg-violet/10 px-3 py-2 text-sm font-medium text-violet">{match.status_text}</div>

      <div className="mt-5 rounded-xl border border-line bg-surface2/60 p-4">
        <div className="label mb-2 flex items-center gap-1.5 text-accent"><Sparkles size={12} /> 30-second catch-up preview</div>
        {recap.loading && <div className="space-y-2"><div className="skeleton h-4" /><div className="skeleton h-4 w-11/12" /><div className="skeleton h-4 w-4/5" /></div>}
        {recap.error && <p className="text-sm text-mute">Preview unavailable right now.</p>}
        {recap.data && <p className="text-sm leading-relaxed text-ink/90">{recap.data.paragraphs.slice(0, 2).join(' ')}</p>}
      </div>

      <button onClick={() => nav(`/match/${match.id}/catch-up`, { state: { auto: true } })} className="btn btn-primary mt-5 w-full">
        <Sparkles size={16} /> Catch Me Up <ArrowRight size={16} />
      </button>
    </div>
  )
}

export default function Home() {
  const nav = useNavigate()
  const [q, setQ] = useState('')
  const [cat, setCat] = useState('recent')
  const demo = useApi(() => api.matches({ category: 'demo', limit: 8 }), [])
  const list = useApi(() => api.matches({ category: cat, limit: 6 }), [cat])
  const featured = demo.data?.items?.[0]

  const search = (e) => { e.preventDefault(); nav(`/matches${q.trim() ? `?q=${encodeURIComponent(q.trim())}` : ''}`) }

  return (
    <>
      <section className="relative">
        <HeroBackground />
        <div className="mx-auto grid max-w-7xl gap-10 px-4 pb-16 pt-12 sm:px-6 sm:pt-20 lg:grid-cols-[1.1fr_.9fr] lg:items-center">
          <div className="animate-rise">
            <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-accent/30 bg-accent/10 px-3 py-1 text-xs font-semibold text-accent">
              <Zap size={13} /> Joined late? We've got you.
            </div>
            <h1 className="font-display text-4xl font-bold leading-[1.05] sm:text-6xl">
              Missed the match?<br /><span className="text-accent">Catch up in 30 seconds.</span>
            </h1>
            <p className="mt-5 max-w-xl text-base text-mute sm:text-lg">
              Get the complete story behind every cricket match with AI-powered summaries, key moments, player insights and match analysis.
            </p>
            <form onSubmit={search} className="mt-8 flex max-w-xl flex-col gap-3 sm:flex-row">
              <label className="relative flex-1">
                <span className="sr-only">Search matches</span>
                <Search size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-mute" />
                <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search team, venue or tournament"
                  className="w-full rounded-xl border border-line bg-surface py-3 pl-10 pr-3 text-sm outline-none transition focus:border-accent" />
              </label>
              <button className="btn btn-ghost" type="submit">Search</button>
            </form>
            <div className="mt-4 flex flex-wrap gap-3">
              <Link to="/matches" className="btn btn-primary">Explore matches <ArrowRight size={16} /></Link>
              <Link to="/live-demo" className="btn btn-ghost"><Zap size={16} /> Live stream demo</Link>
              {featured && <Link to={`/match/${featured.id}/catch-up`} state={{ auto: true }} className="btn btn-ghost"><Sparkles size={16} /> Try a demo catch-up</Link>}
            </div>
            <ul className="mt-8 flex flex-wrap gap-x-6 gap-y-2 text-sm text-mute">
              <li className="flex items-center gap-2"><Clock size={14} className="text-accent" /> Recap in seconds</li>
              <li className="flex items-center gap-2"><Bot size={14} className="text-accent" /> Runs offline, no API keys</li>
              <li className="flex items-center gap-2"><BarChart3 size={14} className="text-accent" /> Every number from real ball-by-ball data</li>
            </ul>
          </div>

          <div className="animate-rise" style={{ animationDelay: '.1s' }}>
            {demo.loading && <Loading rows={2} label="Loading featured match" />}
            {demo.error && <ErrorBox message={demo.error} onRetry={demo.reload} />}
            {featured && <FeaturedMatch match={featured} />}
            {demo.data && !featured && <Empty title="No demo match loaded">Run the ingestion script to load matches.</Empty>}
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4 sm:px-6">
        <SectionTitle eyebrow="Matches" title="Pick a match, join in the middle">
          Every card is labelled by data type. Live scores are never simulated - demo matches are real historical games replayed from a chosen moment.
        </SectionTitle>
        <div className="mb-5 flex flex-wrap gap-2" role="tablist" aria-label="Match categories">
          {CATEGORIES.map((c) => (
            <button key={c.id} role="tab" aria-selected={cat === c.id} onClick={() => setCat(c.id)} className={`chip ${cat === c.id ? 'chip-on' : ''}`}>
              {c.id === 'live' && <span className="h-1.5 w-1.5 rounded-full bg-rose" />} {c.label}
            </button>
          ))}
        </div>
        {list.loading && <Loading rows={2} />}
        {list.error && <ErrorBox message={list.error} onRetry={list.reload} />}
        {list.data && list.data.items.length === 0 && (
          <Empty title={`No ${cat} matches`}>
            {list.data.notice}
            <div className="mt-4"><Link to="/matches?category=demo" className="btn btn-ghost">Browse demo matches</Link></div>
          </Empty>
        )}
        {list.data && list.data.items.length > 0 && (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{list.data.items.map((m) => <MatchCard key={m.id} match={m} />)}</div>
        )}

        {demo.data?.items?.length > 1 && (
          <div className="mt-12">
            <div className="mb-4 flex items-center gap-3"><DataBadge kind="DEMO" /><h3 className="font-display text-xl font-semibold">Join a match in progress</h3></div>
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{demo.data.items.map((m) => <MatchCard key={m.id} match={m} />)}</div>
          </div>
        )}
      </section>

      <section className="mx-auto mt-24 max-w-7xl px-4 sm:px-6">
        <SectionTitle eyebrow="How it works" title="From first ball to full story">
          Python does the cricket maths. The AI only explains what the data says.
        </SectionTitle>
        <div className="grid gap-4 md:grid-cols-3">
          {[
            [MousePointerClick, '1. Open any match', 'See the score, run rate, target and who is at the crease the moment you arrive.'],
            [Sparkles, '2. Tap "Catch Me Up"', 'Quick, standard or detailed recap, tuned to what you care about: players, wickets, milestones or the situation.'],
            [MessageCircle, '3. Dig deeper', 'Explore the timeline, turning points and milestones - then ask anything. Answers are computed from the data.'],
          ].map(([Icon, t, d]) => (
            <div key={t} className="card-pad"><Icon className="mb-3 text-accent" size={22} /><div className="font-display text-lg font-semibold">{t}</div><p className="mt-1.5 text-sm text-mute">{d}</p></div>
          ))}
        </div>
        <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[
            [Clock, 'Match timeline', 'Wickets, boundaries, milestones and turning points in order.', 'timeline'],
            [BarChart3, 'Player insights', 'Verified batting, bowling and fielding with charts.', 'players'],
            [Award, 'Milestone tracker', 'Fifties, hundreds, wicket hauls, partnerships, team landmarks.', 'milestones'],
            [TrendingUp, 'Momentum', 'Ranked turning points on a derived momentum chart.', 'momentum'],
          ].map(([Icon, t, d, tab]) => (
            <Link key={t} to={featured ? `/match/${featured.id}/${tab}` : '/matches'} className="card-pad transition hover:border-accent/50">
              <Icon className="mb-2 text-sky" size={20} /><div className="font-semibold">{t}</div><p className="mt-1 text-sm text-mute">{d}</p>
            </Link>
          ))}
        </div>
        <Notice tone="info" className="mt-8">
          Data: historical ball-by-ball records from <a className="underline" href="https://cricsheet.org/" target="_blank" rel="noreferrer">Cricsheet</a>.
          No free, documented live-score feed is bundled, so MatchBack AI never shows a live score it cannot verify.
        </Notice>
      </section>
    </>
  )
}
