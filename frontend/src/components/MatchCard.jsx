import { Link } from 'react-router-dom'
import { Calendar, MapPin, ChevronRight, Sparkles } from 'lucide-react'
import { DataBadge, TeamBadge } from './ui'
import { FORMAT_LABEL, fmtDate } from '../lib/format'

export default function MatchCard({ match }) {
  const isDemo = match.data_kind === 'DEMO'
  return (
    <Link to={`/match/${match.id}`} className="card group flex flex-col gap-4 p-4 transition hover:-translate-y-0.5 hover:border-accent/50 hover:shadow-glow sm:p-5">
      <div className="flex flex-wrap items-center gap-2">
        <DataBadge kind={match.data_kind} small />
        <span className="rounded-full bg-surface2 px-2.5 py-0.5 text-[11px] font-semibold text-ink">{FORMAT_LABEL[match.format]}</span>
        {match.gender === 'female' && <span className="rounded-full bg-surface2 px-2.5 py-0.5 text-[11px] font-semibold text-mute">Women</span>}
        <span className="ml-auto truncate text-xs text-mute">{match.tournament}{match.stage ? ` · ${match.stage}` : ''}</span>
      </div>

      <div className="space-y-3">
        {match.teams.map((t) => {
          const sc = (match.scores || []).filter((s) => s.team === t.name)
          return (
            <div key={t.name} className="flex items-center gap-3">
              <TeamBadge team={t} />
              <div className="min-w-0 flex-1 truncate font-semibold">{t.name}</div>
              <div className="text-right">
                {sc.length ? sc.map((s, i) => (
                  <div key={i} className="num font-display text-lg font-bold leading-tight">
                    {s.score}<span className="ml-1.5 text-xs font-medium text-mute">({s.overs} ov)</span>
                  </div>
                )) : <span className="text-sm text-mute">Yet to bat</span>}
              </div>
            </div>
          )
        })}
      </div>

      <div className={`rounded-lg px-3 py-2 text-sm font-medium ${isDemo ? 'bg-violet/10 text-violet' : 'bg-surface2 text-ink'}`}>
        {match.status_text}
      </div>

      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-mute">
        <span className="inline-flex items-center gap-1"><Calendar size={12} /> {fmtDate(match.date)}</span>
        {match.venue && <span className="inline-flex min-w-0 items-center gap-1"><MapPin size={12} /> <span className="truncate">{match.venue}</span></span>}
        <span className="ml-auto inline-flex items-center gap-1 font-semibold text-accent opacity-80 transition group-hover:opacity-100">
          {isDemo ? <><Sparkles size={13} /> Catch me up</> : 'Open match'} <ChevronRight size={14} />
        </span>
      </div>
    </Link>
  )
}
