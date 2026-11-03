import { useEffect, useRef, useState } from 'react'
import { Bot, Cpu, MessageCircle, Send, Sparkles, X } from 'lucide-react'
import { api, errorMessage } from '../lib/api'
import { useApi } from '../lib/hooks'
import { Spinner } from './ui'

export default function AskWidget({ matchId, at, match }) {
  const [open, setOpen] = useState(false)
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [msgs, setMsgs] = useState([])
  const endRef = useRef(null)
  const inputRef = useRef(null)
  const sugg = useApi(() => (open ? api.suggestions(matchId, at) : Promise.resolve(null)), [open, matchId, at])

  useEffect(() => { setMsgs([]) }, [matchId])
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }) }, [msgs, busy])
  useEffect(() => {
    if (!open) return undefined
    inputRef.current?.focus()
    const onKey = (e) => e.key === 'Escape' && setOpen(false)
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open])

  const send = async (text) => {
    const question = (text ?? input).trim()
    if (!question || busy) return
    setInput('')
    setMsgs((m) => [...m, { role: 'user', text: question }])
    setBusy(true)
    try {
      const r = await api.ask(matchId, { question, at })
      setMsgs((m) => [...m, { role: 'ai', text: r.answer, engine: r.engine, intent: r.intent, suggestions: r.intent === 'unknown' ? r.suggestions : [] }])
    } catch (e) {
      setMsgs((m) => [...m, { role: 'ai', error: true, text: errorMessage(e) }])
    } finally { setBusy(false) }
  }

  const chips = (sugg.data?.suggestions || []).filter((s) => !msgs.some((m) => m.text === s))

  return (
    <>
      {!open && (
        <button onClick={() => setOpen(true)} className="btn btn-primary fixed bottom-5 right-4 z-50 !rounded-full !px-5 !py-3.5 sm:right-6" aria-label="Open Ask MatchBack AI">
          <MessageCircle size={18} /> <span className="hidden sm:inline">Ask MatchBack AI</span><span className="sm:hidden">Ask AI</span>
        </button>
      )}
      {open && (
        <section role="dialog" aria-label="Ask MatchBack AI"
          className="fixed inset-x-0 bottom-0 z-50 flex max-h-[85vh] flex-col rounded-t-3xl border border-line bg-surface shadow-2xl sm:inset-x-auto sm:bottom-5 sm:right-6 sm:h-[600px] sm:w-[400px] sm:rounded-3xl">
          <header className="flex items-center gap-3 border-b border-line px-4 py-3">
            <span className="grid h-9 w-9 place-items-center rounded-xl bg-accent/15 text-accent"><Bot size={18} /></span>
            <div className="min-w-0 flex-1">
              <div className="font-display font-semibold leading-tight">Ask MatchBack AI</div>
              <div className="truncate text-xs text-mute">{match.title} · {match.data_kind === 'DEMO' ? 'demo replay' : 'historical'}</div>
            </div>
            <button onClick={() => setOpen(false)} className="btn btn-ghost !p-2" aria-label="Close assistant"><X size={16} /></button>
          </header>

          <div className="flex-1 space-y-3 overflow-y-auto px-4 py-4" aria-live="polite">
            {msgs.length === 0 && (
              <div className="rounded-2xl bg-surface2 p-4 text-sm text-mute">
                <Sparkles size={16} className="mb-2 text-accent" />
                Ask about the score, scorers, wickets, partnerships, turning points or milestones. Answers are calculated from this match's data, and I'll say so if something isn't available.
              </div>
            )}
            {msgs.map((m, i) => (
              <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : ''}`}>
                <div className={`max-w-[92%] rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed ${m.role === 'user' ? 'bg-accent text-accent-ink' : m.error ? 'border border-rose/40 bg-rose/10 text-rose' : 'bg-surface2'}`}>
                  {m.text}
                  {m.engine && <div className="mt-2 flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wider text-mute"><Cpu size={10} /> {m.engine}</div>}
                  {m.suggestions?.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1.5">{m.suggestions.slice(0, 4).map((s) => <button key={s} onClick={() => send(s)} className="chip !text-[11px]">{s}</button>)}</div>
                  )}
                </div>
              </div>
            ))}
            {busy && <div className="flex"><div className="rounded-2xl bg-surface2 px-4 py-3 text-mute"><Spinner /></div></div>}
            <div ref={endRef} />
          </div>

          {chips.length > 0 && (
            <div className="scroll-x flex gap-2 border-t border-line px-4 py-2.5" aria-label="Suggested questions">
              {chips.slice(0, 8).map((s) => <button key={s} onClick={() => send(s)} disabled={busy} className="chip shrink-0 whitespace-nowrap">{s}</button>)}
            </div>
          )}
          <form onSubmit={(e) => { e.preventDefault(); send() }} className="flex gap-2 border-t border-line p-3">
            <input ref={inputRef} value={input} onChange={(e) => setInput(e.target.value)} maxLength={500} placeholder="Ask about this match..."
              aria-label="Your question" className="min-w-0 flex-1 rounded-xl border border-line bg-bg px-3.5 py-2.5 text-sm outline-none focus:border-accent" />
            <button type="submit" disabled={busy || !input.trim()} className="btn btn-primary !px-3.5" aria-label="Send question"><Send size={16} /></button>
          </form>
        </section>
      )}
    </>
  )
}
