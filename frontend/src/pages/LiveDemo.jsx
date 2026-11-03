import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { ChevronLeft, FastForward, FileVideo, Pause, Play, RotateCcw, Sparkles, X } from 'lucide-react'
import AskWidget from '../components/AskWidget'
import { TABS, TabBody, TabNav, TOAST_ICON, TOAST_TONE } from '../components/StreamParts'
import { ErrorBox, Loading, Notice, TeamBadge } from '../components/ui'
import { api, errorMessage } from '../lib/api'
import { loadStream, tickerAt } from '../lib/stream'

const BALL_SECONDS = 3 // demo pace: one delivery per 3 s at 1x

/** Neutral stand-in for the broadcast feed (no footage is bundled). */
function StreamPlaceholder() {
  return (
    <div className="absolute inset-0 overflow-hidden bg-gradient-to-br from-emerald-900 via-emerald-800 to-slate-900" aria-hidden="true">
      <svg viewBox="0 0 640 360" className="absolute inset-0 h-full w-full opacity-40" fill="none" preserveAspectRatio="xMidYMid slice">
        <ellipse cx="320" cy="190" rx="290" ry="150" stroke="white" strokeOpacity=".5" strokeWidth="2" />
        <ellipse cx="320" cy="190" rx="170" ry="85" stroke="white" strokeOpacity=".3" strokeWidth="1.5" strokeDasharray="6 8" />
        <rect x="302" y="120" width="36" height="140" rx="4" fill="white" fillOpacity=".12" stroke="white" strokeOpacity=".5" />
        <path d="M312 120v-10M320 120v-10M328 120v-10M312 260v10M320 260v10M328 260v10" stroke="white" strokeOpacity=".7" strokeWidth="2" strokeLinecap="round" />
      </svg>
      <div className="absolute inset-0 grid place-items-center text-center text-white/80"><div><div className="font-display text-lg font-semibold">Stream area</div><div className="text-xs">Footage plugs in here · pick your own clip below to try it</div></div></div>
    </div>
  )
}

export default function LiveDemo() {
  const [list, setList] = useState({ items: [], error: null })
  const [matchId, setMatchId] = useState(null)
  const [st, setSt] = useState({ data: null, loading: false, error: null })
  const [seq, setSeq] = useState(0)
  const [playing, setPlaying] = useState(true)
  const [speed, setSpeed] = useState(1)
  const [tab, setTab] = useState(() => { const t = new URLSearchParams(window.location.search).get('tab'); return TABS.some(([k]) => k === t) ? t : 'live' })
  const [aiAt, setAiAt] = useState(null)
  const [matchAt, setMatchAt] = useState(null)
  const [toast, setToast] = useState(null)
  const [banner, setBanner] = useState(true)
  const [autoCatchUp, setAutoCatchUp] = useState(false)
  const [videoUrl, setVideoUrl] = useState(null) // object URL of a clip the user picked locally (never uploaded)
  const [videoName, setVideoName] = useState('')
  const video = useRef(null)

  // The stream screen uses the light, app-style skin; restore the user's theme on exit.
  useEffect(() => {
    const prev = document.documentElement.getAttribute('data-theme')
    document.documentElement.setAttribute('data-theme', 'light')
    return () => document.documentElement.setAttribute('data-theme', prev || 'dark')
  }, [])
  useEffect(() => () => { if (videoUrl) URL.revokeObjectURL(videoUrl) }, [videoUrl])

  useEffect(() => {
    api.matches({ category: 'demo', limit: 8 })
      .then((d) => { const items = d.items.filter((m) => m.format !== 'TEST'); setList({ items, error: null }); if (items[0]) setMatchId(items[0].id) })
      .catch((e) => setList({ items: [], error: errorMessage(e) }))
  }, [])

  useEffect(() => {
    if (!matchId) return undefined
    let live = true
    setSt({ data: null, loading: true, error: null }); setMatchAt(null); setToast(null); setBanner(true)
    loadStream(matchId)
      .then((d) => { if (!live) return; setSt({ data: d, loading: false, error: null }); setSeq(d.details.replay.default_seq); setAiAt(d.details.replay.default_seq); setPlaying(true) })
      .catch((e) => live && setSt({ data: null, loading: false, error: errorMessage(e) }))
    return () => { live = false }
  }, [matchId])

  // replay clock: one delivery every BALL_SECONDS / speed while "playing"
  useEffect(() => {
    if (!playing || !st.data) return undefined
    const id = setInterval(() => setSeq((s) => {
      if (s >= st.data.max) { setPlaying(false); return s }
      const n = s + 1
      const ev = st.data.bySeq.get(n)
      if (ev) setToast({ ...ev[ev.length - 1], key: `${n}-${Date.now()}` })
      return n
    }), (BALL_SECONDS * 1000) / speed)
    return () => clearInterval(id)
  }, [playing, speed, st.data])

  useEffect(() => { const v = video.current; if (!v) return; if (playing) v.play().catch(() => {}); else v.pause() }, [playing, videoUrl])
  useEffect(() => { if (!toast) return undefined; const t = setTimeout(() => setToast(null), 5000); return () => clearTimeout(t) }, [toast])

  // AI panels use a snapshot position; refreshed on demand so heavy panels don't refetch every ball.
  useEffect(() => {
    if (aiAt === null || !matchId) return undefined
    let live = true
    api.match(matchId, aiAt).then((m) => live && setMatchAt(m)).catch(() => {})
    return () => { live = false }
  }, [aiAt, matchId])

  const format = st.data?.details.format
  const d = st.data?.details
  const tick = useMemo(() => (st.data ? tickerAt(st.data, Math.min(seq, st.data.max), format) : null), [st.data, seq, format])
  const ctx = useMemo(() => (matchAt ? { match: matchAt, id: matchId, at: aiAt, search: '', embedded: true, autoStart: autoCatchUp } : null), [matchAt, matchId, aiAt, autoCatchUp])
  const sync = useCallback(() => setAiAt(seq), [seq])
  const openTab = (t) => { setTab(t); if (t !== 'live') setAiAt(seq) }
  const jumpTo = (s) => { setSeq(s); setAiAt(s); setToast(null) }
  const stale = aiAt !== null && seq - aiAt >= 6
  const pickVideo = (f) => { if (!f) return; if (videoUrl) URL.revokeObjectURL(videoUrl); setVideoUrl(URL.createObjectURL(f)); setVideoName(f.name) }

  const cur = st.data ? st.data.balls[Math.min(seq, st.data.max)] : null
  const overBalls = st.data && cur ? st.data.balls.slice(0, seq + 1).filter((b) => b.innings_no === cur.innings_no && b.over_no === cur.over_no) : []
  const feed = st.data ? st.data.events.filter((e) => e.seq <= seq).slice(-6).reverse() : []
  const ToastIcon = toast ? TOAST_ICON[toast.type] : null
  const teamLine = (name) => (tick.team === name ? `${tick.score} (${tick.overs} ov)` : st.data.inn1Team === name ? `${st.data.inn1Score} (innings done)` : 'yet to bat')

  return (
    <div className="min-h-screen bg-bg">
      <header className="sticky top-0 z-40 text-white" style={{ background: 'linear-gradient(90deg,#b4101f,#d8283a)' }}>
        <div className="mx-auto flex h-14 max-w-5xl items-center gap-3 px-4">
          <Link to="/" className="rounded-lg p-1.5 hover:bg-white/15" aria-label="Back to MatchBack AI"><ChevronLeft size={20} /></Link>
          <div className="min-w-0 flex-1">
            <div className="truncate font-display text-base font-bold leading-tight">{d ? d.title : 'Live stream'}</div>
            <div className="truncate text-[11px] text-white/80">{d ? `${d.tournament || ''} · ${d.format}` : 'Prototype: live-stream insights'}</div>
          </div>
          <span className="inline-flex items-center gap-1.5 rounded-full bg-white/15 px-2.5 py-1 text-[11px] font-bold tracking-wider"><span className="h-1.5 w-1.5 animate-pulseDot rounded-full bg-white" /> DEMO STREAM</span>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-0 pb-24 sm:px-4 sm:pt-4">
        {list.error && <div className="p-4"><ErrorBox message={list.error} /></div>}
        {st.loading && <div className="p-4"><Loading rows={2} label="Loading the stream" /></div>}
        {st.error && <div className="p-4"><ErrorBox message={st.error} onRetry={() => setMatchId((m) => m + '')} /></div>}

        {st.data && tick && (
          <>
            <section className="overflow-hidden bg-black sm:rounded-2xl">
              <div className="relative aspect-video w-full">
                {videoUrl ? <video ref={video} src={videoUrl} muted loop playsInline autoPlay className="absolute inset-0 h-full w-full object-cover" aria-label="Your video" /> : <StreamPlaceholder />}
                <div className="absolute left-3 top-3 flex items-center gap-2 text-[10px] font-bold">
                  <span className="rounded bg-violet px-2 py-1 text-white">DEMO STREAM</span>
                  <span className="rounded bg-black/55 px-2 py-1 text-white/90">{videoUrl ? videoName : 'no footage attached'} · replayed match</span>
                </div>
                {toast && (
                  <div key={toast.key} className={`absolute right-3 top-12 max-w-[78%] animate-rise rounded-xl border-l-4 bg-black/75 p-3 text-white backdrop-blur ${TOAST_TONE[toast.type] || 'border-accent'}`}>
                    <div className="flex items-center gap-2 text-xs font-bold">{ToastIcon && <ToastIcon size={14} />}{toast.badge || toast.title}</div>
                    <div className="mt-0.5 text-[11px] text-white/80">{toast.description}</div>
                  </div>
                )}
                <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/85 to-transparent p-3 pt-10 text-white">
                  <div className="flex items-end gap-3">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-baseline gap-2">
                        <span className="num font-display text-2xl font-bold sm:text-3xl">{d.teams.find((t) => t.name === tick.team)?.abbr || tick.team.slice(0, 3).toUpperCase()} {tick.score}</span>
                        <span className="num text-sm text-white/80">({tick.overs} ov)</span>
                      </div>
                      <div className="truncate text-xs font-semibold text-white/85">{tick.status}{tick.rr !== '-' ? ` · CRR ${tick.rr}` : ''}{tick.rrr ? ` · RRR ${tick.rrr}` : ''}</div>
                    </div>
                    <div className="flex shrink-0 items-center gap-1.5">
                      <button onClick={() => setPlaying((p) => !p)} className="grid h-9 w-9 place-items-center rounded-full bg-white/20 hover:bg-white/30" aria-label={playing ? 'Pause' : 'Play'}>{playing ? <Pause size={16} /> : <Play size={16} />}</button>
                      <button onClick={() => setSpeed((s) => (s === 1 ? 3 : s === 3 ? 8 : 1))} className="inline-flex h-9 items-center gap-1 rounded-full bg-white/20 px-3 text-xs font-bold hover:bg-white/30" aria-label="Change replay speed"><FastForward size={13} />{speed}x</button>
                    </div>
                  </div>
                </div>
              </div>
              <div className="bg-slate-900 px-3 py-2.5 text-white">
                <input type="range" min={11} max={st.data.max} value={seq} onChange={(e) => setSeq(+e.target.value)} onMouseUp={(e) => jumpTo(+e.target.value)} onTouchEnd={(e) => jumpTo(+e.target.value)}
                  onKeyUp={(e) => jumpTo(+e.target.value)} aria-label="Match position" className="w-full accent-[#ff4d5e]" />
                <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-white/70">
                  <span>Innings {tick.innings} · {tick.overs} ov</span>
                  <button onClick={() => jumpTo(12)} className="inline-flex items-center gap-1 hover:text-white"><RotateCcw size={11} /> From the start</button>
                  <button onClick={() => jumpTo(d.replay.default_seq)} className="hover:text-white">Join mid-match</button>
                  <label className="inline-flex cursor-pointer items-center gap-1 hover:text-white"><FileVideo size={11} /> Use my own video<input type="file" accept="video/*" className="sr-only" onChange={(e) => pickVideo(e.target.files?.[0])} /></label>
                  <span className="ml-auto">Real match data, replayed. Not live.</span>
                </div>
              </div>
            </section>

            <section className="mt-3 bg-surface px-4 py-3 sm:rounded-2xl sm:border sm:border-line">
              <div className="flex items-center gap-3">
                {d.teams.map((t, i) => (
                  <div key={t.name} className={`flex flex-1 items-center gap-2.5 ${i === 1 ? 'flex-row-reverse text-right' : ''}`}>
                    <TeamBadge team={t} size={38} />
                    <div className="min-w-0"><div className="truncate text-sm font-semibold">{t.name}</div><div className="num text-xs text-mute">{teamLine(t.name)}</div></div>
                  </div>
                ))}
              </div>
              <div className="mt-2 rounded-lg bg-surface2 px-3 py-2 text-center text-sm font-semibold">{tick.status}</div>
            </section>

            {banner && seq < st.data.max && (
              <section className="mx-4 mt-3 flex items-center gap-3 rounded-2xl border border-accent/40 bg-accent/10 p-3.5 sm:mx-0">
                <Sparkles className="shrink-0 text-accent" size={20} />
                <div className="min-w-0 flex-1 text-sm"><b>Just joined?</b> <span className="text-mute">Get everything you missed in 30 seconds.</span></div>
                <button onClick={() => { setAutoCatchUp(true); openTab('catchup'); setBanner(false) }} className="btn btn-primary !px-4 !py-2 text-xs">Catch Me Up</button>
                <button onClick={() => setBanner(false)} className="rounded-lg p-1.5 text-mute hover:bg-surface2" aria-label="Dismiss"><X size={14} /></button>
              </section>
            )}

            {list.items.length > 1 && (
              <div className="scroll-x mt-3 flex gap-2 px-4 sm:px-0" aria-label="Choose a demo match">
                {list.items.map((m) => <button key={m.id} onClick={() => setMatchId(m.id)} className={`chip shrink-0 whitespace-nowrap ${matchId === m.id ? 'chip-on' : ''}`}>{m.title} · {m.format}</button>)}
              </div>
            )}

            <TabNav tab={tab} onOpen={openTab} />
            <div className="mt-4 px-4 sm:px-0">
              {tab !== 'live' && stale && (
                <div className="mb-3 flex items-center gap-3 rounded-xl border border-amber/40 bg-amber/10 px-3.5 py-2.5 text-sm">
                  <span className="min-w-0 flex-1 text-amber">Insights are as of an earlier ball — the match has moved on.</span>
                  <button onClick={sync} className="btn btn-ghost !px-3 !py-1.5 text-xs">Update to now</button>
                </div>
              )}
              <TabBody tab={tab} ctx={ctx} tick={tick} cur={cur} overBalls={overBalls} feed={feed} onOpen={openTab} />
              <Notice tone="demo" className="mt-6">
                <b>Prototype.</b> No footage is bundled. Scores come from a real historical match replayed ball by ball, so nothing here is live. Every AI insight only uses play up to the position shown.
              </Notice>
            </div>
          </>
        )}
      </main>
      {matchAt && <AskWidget matchId={matchId} at={aiAt} match={matchAt} />}
    </div>
  )
}
