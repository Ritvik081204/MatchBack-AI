import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Award, Check, Copy, Cpu, Info, Sparkles, Timer, TrendingUp } from 'lucide-react'
import { ErrorBox, Notice, Spinner } from '../../components/ui'
import { useMatchCtx } from '../../lib/matchContext'
import { api, errorMessage } from '../../lib/api'
import { useApi } from '../../lib/hooks'

const LENGTHS = [
  ['quick', 'Quick recap', '~30 seconds'],
  ['standard', 'Standard recap', '~1 minute'],
  ['detailed', 'Detailed recap', 'comprehensive'],
]
const FOCUS = [
  ['everything', 'Everything important'],
  ['players', 'Player performances'],
  ['wickets', 'Wickets & turning points'],
  ['milestones', 'Records & milestones'],
  ['situation', 'Match situation'],
]

export default function CatchUp() {
  const { match: m, id, at, search, embedded, autoStart } = useMatchCtx()
  const location = useLocation()
  const [length, setLength] = useState('quick')
  const [focus, setFocus] = useState('everything')
  const [started, setStarted] = useState(Boolean(location.state?.auto) || Boolean(autoStart) ||new URLSearchParams(location.search).get('go') === '1')
  const [res, setRes] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [copied, setCopied] = useState(false)
  const reqId = useRef(0)

  const generate = useCallback(() => {
    const mine = ++reqId.current
    setBusy(true); setError(null)
    api.catchUp(id, { length, focus, at })
      .then((r) => mine === reqId.current && setRes(r))
      .catch((e) => mine === reqId.current && setError(errorMessage(e)))
      .finally(() => mine === reqId.current && setBusy(false))
  }, [id, at, length, focus])

  // After the first "Catch Me Up", changing length / focus / replay position regenerates automatically.
  useEffect(() => { if (started) generate() }, [started, generate])

  const tps = useApi(() => (started ? api.turningPoints(id, at) : Promise.resolve(null)), [started, id, at])
  const ms = useApi(() => (started ? api.milestones(id, at) : Promise.resolve(null)), [started, id, at])

  const copy = async () => {
    try { await navigator.clipboard.writeText(res.paragraphs.join('\n\n')); setCopied(true); setTimeout(() => setCopied(false), 1800) } catch { /* clipboard blocked */ }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[360px_1fr]">
      <aside className="card-pad h-fit space-y-6 lg:sticky lg:top-36">
        <div>
          <div className="label mb-2">1. How much time do you have?</div>
          <div className="space-y-2" role="radiogroup" aria-label="Recap length">
            {LENGTHS.map(([v, l, d]) => (
              <button key={v} role="radio" aria-checked={length === v} onClick={() => setLength(v)}
                className={`flex w-full items-center justify-between rounded-xl border px-3.5 py-2.5 text-left text-sm transition ${length === v ? 'border-accent bg-accent/10' : 'border-line hover:border-accent/40'}`}>
                <span className="font-semibold">{l}</span><span className="text-xs text-mute">{d}</span>
              </button>
            ))}
          </div>
        </div>
        <div>
          <div className="label mb-2">2. What do you want to understand?</div>
          <div className="flex flex-wrap gap-2" role="radiogroup" aria-label="Recap focus">
            {FOCUS.map(([v, l]) => <button key={v} role="radio" aria-checked={focus === v} onClick={() => setFocus(v)} className={`chip ${focus === v ? 'chip-on' : ''}`}>{l}</button>)}
          </div>
        </div>
        <button onClick={() => (started ? generate() : setStarted(true))} disabled={busy} className="btn btn-primary w-full !py-3.5 text-base">
          {busy ? <Spinner /> : <Sparkles size={18} />} {started ? 'Regenerate' : 'Catch Me Up'}
        </button>
        <p className="text-xs text-mute">
          Facts are computed in Python from the ball-by-ball data. {m.data_kind === 'DEMO' ? 'Only play up to the replay position is used.' : ''}
        </p>
      </aside>

      <div className="space-y-6">
        {!started && (
          <div className="card-pad flex flex-col items-center gap-3 py-16 text-center">
            <Sparkles className="text-accent" size={34} />
            <h2 className="font-display text-2xl font-bold">Ready when you are</h2>
            <p className="max-w-md text-sm text-mute">Pick a length and focus, then tap <b>Catch Me Up</b> for the story of this match so far.</p>
          </div>
        )}
        {error && <ErrorBox message={error} onRetry={generate} />}
        {busy && !res && <div className="card-pad"><div className="space-y-3"><div className="skeleton h-5 w-2/3" /><div className="skeleton h-4" /><div className="skeleton h-4 w-11/12" /><div className="skeleton h-4 w-4/5" /></div></div>}

        {res && (
          <article className={`card-pad transition ${busy ? 'opacity-60' : ''}`} aria-busy={busy}>
            <div className="mb-4 flex flex-wrap items-center gap-2">
              <span className="rounded-full bg-accent/15 px-3 py-1 text-xs font-bold text-accent">{LENGTHS.find((l) => l[0] === res.length)?.[1]}</span>
              <span className="inline-flex items-center gap-1 text-xs text-mute"><Timer size={12} /> ~{res.read_seconds}s read · {res.word_count} words</span>
              <span className="inline-flex items-center gap-1 text-xs text-mute"><Cpu size={12} /> {res.engine === 'rule-based' ? 'Rule-based writer (verified facts)' : res.engine}</span>
              <span className="ml-auto text-xs text-mute">as of innings {res.as_of.innings}: {res.as_of.score} ({res.as_of.overs} ov) · {res.generated_ms} ms</span>
            </div>
            <div className="space-y-3.5 text-[15px] leading-relaxed">
              {res.paragraphs.map((p, i) => <p key={i} className="animate-rise" style={{ animationDelay: `${i * 60}ms` }}>{p}</p>)}
            </div>
            {res.note && <Notice tone="info" className="mt-5"><Info size={14} className="mr-1.5 inline" />{res.note}</Notice>}
            <div className="mt-5 flex flex-wrap gap-2 border-t border-line pt-4">
              <button onClick={copy} className="btn btn-ghost !py-2 text-xs">{copied ? <Check size={14} /> : <Copy size={14} />} {copied ? 'Copied' : 'Copy recap'}</button>
              {!embedded && <Link to={{ pathname: `/match/${id}/timeline`, search }} className="btn btn-ghost !py-2 text-xs">See the timeline</Link>}
              {!embedded && <Link to={{ pathname: `/match/${id}/players`, search }} className="btn btn-ghost !py-2 text-xs">Player insights</Link>}
            </div>
          </article>
        )}

        {res && (
          <div className="grid gap-4 md:grid-cols-2">
            <section className="card-pad">
              <h3 className="mb-3 flex items-center gap-2 font-display text-base font-semibold"><TrendingUp size={16} className="text-accent" /> Key moments</h3>
              {tps.data?.turning_points?.length ? [...tps.data.turning_points].sort((a, b) => a.rank - b.rank).slice(0, 3).map((t) => (
                <div key={t.id} className="mb-3 border-l-2 border-accent/60 pl-3 text-sm last:mb-0">
                  <div className="text-xs font-semibold text-accent">{t.label} · overs {t.start_over}-{t.end_over}</div>
                  <div className="text-mute">{t.explanation}</div>
                </div>
              )) : <p className="text-sm text-mute">{tps.loading ? 'Loading...' : 'None detected yet.'}</p>}
            </section>
            <section className="card-pad">
              <h3 className="mb-3 flex items-center gap-2 font-display text-base font-semibold"><Award size={16} className="text-amber" /> Milestones so far</h3>
              {ms.data?.milestones?.filter((x) => x.category !== 'team').length ? ms.data.milestones.filter((x) => x.category !== 'team').slice(-4).reverse().map((x) => (
                <div key={x.id} className="mb-3 text-sm last:mb-0"><div className="text-xs font-bold text-amber">{x.badge}</div><div className="text-mute">{x.detail}</div></div>
              )) : <p className="text-sm text-mute">{ms.loading ? 'Loading...' : 'None reached yet.'}</p>}
            </section>
          </div>
        )}
      </div>
    </div>
  )
}
