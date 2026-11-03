import { Link } from 'react-router-dom'
import { Award, BarChart3, Bot, Clock, Sparkles, TrendingUp } from 'lucide-react'
import MatchCard from '../components/MatchCard'
import { ErrorBox, Loading, SectionTitle } from '../components/ui'
import { api } from '../lib/api'
import { useApi } from '../lib/hooks'

const INSIGHTS = [
  [Sparkles, 'AI Catch-Up', 'catch-up', 'A 30-second, 1-minute or detailed recap built only from verified match facts, tuned to what you want to know.'],
  [Clock, 'Match Timeline', 'timeline', 'Every wicket, boundary and milestone in order, with over-by-over navigation and a "why it mattered" explanation per event.'],
  [BarChart3, 'Player Insights', 'players', 'Runs, strike rate, economy, catches and partnerships - with minimum-ball thresholds so highlights are fair.'],
  [Award, 'Milestone Tracker', 'milestones', 'Half-centuries, centuries, wicket hauls, big stands and team landmarks, each reported exactly once.'],
  [TrendingUp, 'Momentum & Turning Points', 'momentum', 'Rule-based detection of collapses, big overs and scoring shifts, ranked by measured impact.'],
]

export default function Insights() {
  const demo = useApi(() => api.matches({ category: 'demo', limit: 8 }), [])
  const first = demo.data?.items?.[0]
  return (
    <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6">
      <SectionTitle eyebrow="Match Insights" title="Five ways to understand a match fast">
        Pick a feature to open it on the featured demo match, or choose any match below.
      </SectionTitle>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {INSIGHTS.map(([Icon, title, tab, desc]) => (
          <Link key={tab} to={first ? `/match/${first.id}/${tab}` : '/matches'} className="card-pad group transition hover:-translate-y-0.5 hover:border-accent/50 hover:shadow-glow">
            <Icon className="mb-3 text-accent" size={24} />
            <div className="font-display text-lg font-semibold">{title}</div>
            <p className="mt-1.5 text-sm text-mute">{desc}</p>
            <div className="mt-4 text-sm font-semibold text-accent">Open on {first ? first.title : 'a match'} →</div>
          </Link>
        ))}
        <div className="card-pad">
          <Bot className="mb-3 text-accent" size={24} />
          <div className="font-display text-lg font-semibold">Ask MatchBack AI</div>
          <p className="mt-1.5 text-sm text-mute">A floating assistant on every match page. Factual answers are calculated in Python; it says so when the data doesn't contain an answer.</p>
        </div>
      </div>
      <h3 className="mb-4 mt-14 font-display text-xl font-semibold">Choose a match</h3>
      {demo.loading && <Loading rows={2} />}
      {demo.error && <ErrorBox message={demo.error} onRetry={demo.reload} />}
      {demo.data && <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{demo.data.items.map((m) => <MatchCard key={m.id} match={m} />)}</div>}
    </div>
  )
}
