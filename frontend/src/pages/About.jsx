import { Link } from 'react-router-dom'
import { Database, Cpu, ShieldCheck, Workflow } from 'lucide-react'
import { DataBadge, Notice, SectionTitle } from '../components/ui'
import { api } from '../lib/api'
import { useApi } from '../lib/hooks'

const STEPS = ['Cricsheet ball-by-ball JSON', 'Validate & parse', 'Python statistics engine', 'Events · milestones · turning points', 'Compact fact context', 'Local LLM or rule-based writer', 'Recap · answers · explanations']

export default function About() {
  const health = useApi(() => api.health(), [])
  const llm = health.data?.llm
  return (
    <div className="mx-auto max-w-4xl px-4 py-10 sm:px-6">
      <SectionTitle eyebrow="About" title="Built so a late joiner understands the match in 30 seconds">
        MatchBack AI turns ball-by-ball data into a story: what happened, who mattered, where it turned, and where the match stands now.
      </SectionTitle>

      <div className="space-y-6">
        <section className="card-pad">
          <h3 className="mb-2 flex items-center gap-2 font-display text-lg font-semibold"><ShieldCheck className="text-accent" size={18} /> The problem</h3>
          <p className="text-sm text-mute">
            Fans who open a match halfway through have to hop between scorecards, commentary feeds and stats pages to work out what they missed.
            MatchBack AI gives one contextual recap, a navigable timeline and answers to follow-up questions.
          </p>
        </section>

        <section className="card-pad">
          <h3 className="mb-3 flex items-center gap-2 font-display text-lg font-semibold"><Workflow className="text-accent" size={18} /> How it works</h3>
          <ol className="flex flex-wrap items-center gap-2 text-xs font-medium">
            {STEPS.map((s, i) => (
              <li key={s} className="flex items-center gap-2"><span className="rounded-lg border border-line bg-surface2 px-2.5 py-1.5">{s}</span>{i < STEPS.length - 1 && <span className="text-accent">→</span>}</li>
            ))}
          </ol>
          <p className="mt-4 text-sm text-mute">
            Python computes every number (scorecards, partnerships, milestones, turning points). Only a compact structured summary - never the raw ball-by-ball
            feed - goes to the language model, and the model's answer is rejected if it introduces a figure that isn't in the facts. With no model installed,
            a deterministic writer produces the recap from the same facts, so nothing breaks.
          </p>
        </section>

        <section className="card-pad">
          <h3 className="mb-3 flex items-center gap-2 font-display text-lg font-semibold"><Database className="text-accent" size={18} /> Data labels</h3>
          <div className="space-y-3 text-sm text-mute">
            <p><DataBadge kind="HISTORICAL" small className="mr-2" />Completed matches from <a className="underline" href="https://cricsheet.org/" target="_blank" rel="noreferrer">Cricsheet</a> ball-by-ball files.</p>
            <p><DataBadge kind="DEMO" small className="mr-2" />A <em>real</em> historical match replayed up to a chosen ball, so you can experience joining mid-match. Nothing after that point is used, and it is never presented as live.</p>
            <p><DataBadge kind="LIVE" small className="mr-2" />Reserved for a future permitted free live feed. None is configured, so no match carries this label today.</p>
          </div>
        </section>

        <section className="card-pad">
          <h3 className="mb-3 flex items-center gap-2 font-display text-lg font-semibold"><Cpu className="text-accent" size={18} /> AI engine status</h3>
          {health.loading ? <p className="text-sm text-mute">Checking...</p> : llm?.available ? (
            <Notice tone="info">Local LLM active: <b>{llm.model}</b> via Ollama. Recaps and explanations use it; every figure is checked against the facts.</Notice>
          ) : (
            <Notice tone="warn">Ollama isn't running, so MatchBack AI is using its built-in rule-based writer ({llm?.reason || health.error || 'server unreachable'}). All features still work.</Notice>
          )}
        </section>

        <section className="card-pad">
          <h3 className="mb-2 font-display text-lg font-semibold">Limitations</h3>
          <ul className="list-disc space-y-1.5 pl-5 text-sm text-mute">
            <li>No live-score API is bundled; demo mode replays historical matches.</li>
            <li>Momentum and "advantage" are derived statistical indicators, not win probabilities.</li>
            <li>Career milestones and fastest-ever claims are not made: only single-match data is loaded.</li>
            <li>Player roles are inferred from what happened in the match; Cricsheet has no official roles.</li>
            <li>The contribution score is a simple custom weighted sum and ignores match context.</li>
          </ul>
        </section>
      </div>
      <div className="mt-8 text-center"><Link to="/matches" className="btn btn-primary">Explore matches</Link></div>
    </div>
  )
}
