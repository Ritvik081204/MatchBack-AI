import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { Search, X } from 'lucide-react'
import MatchCard from '../components/MatchCard'
import { Empty, ErrorBox, Loading, Notice, SectionTitle, Spinner } from '../components/ui'
import { api, errorMessage } from '../lib/api'

const CATS = [['all', 'All'], ['demo', 'Demo (in progress)'], ['recent', 'Recent'], ['completed', 'Completed'], ['live', 'Live'], ['upcoming', 'Upcoming']]
const FORMATS = [['', 'All formats'], ['T20', 'T20'], ['ODI', 'ODI'], ['TEST', 'Test']]
const GENDERS = [['', 'Men & women'], ['male', 'Men'], ['female', 'Women']]
const PAGE = 12

export default function Matches() {
  const [params, setParams] = useSearchParams()
  const category = params.get('category') || 'all'
  const format = params.get('format') || ''
  const gender = params.get('gender') || ''
  const q = params.get('q') || ''
  const [draft, setDraft] = useState(q)
  const [state, setState] = useState({ items: [], total: 0, notice: null, loading: true, error: null, more: false })

  useEffect(() => setDraft(q), [q])

  const fetchPage = (offset) => api.matches({ category, format: format || undefined, gender: gender || undefined, q: q || undefined, limit: PAGE, offset })

  useEffect(() => {
    let live = true
    setState((s) => ({ ...s, loading: true, error: null, items: [] }))
    fetchPage(0)
      .then((d) => live && setState({ items: d.items, total: d.total, notice: d.notice, loading: false, error: null, more: false }))
      .catch((e) => live && setState((s) => ({ ...s, loading: false, error: errorMessage(e) })))
    return () => { live = false }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [category, format, gender, q])

  const loadMore = async () => {
    setState((s) => ({ ...s, more: true }))
    try {
      const d = await fetchPage(state.items.length)
      setState((s) => ({ ...s, items: [...s.items, ...d.items], more: false }))
    } catch (e) { setState((s) => ({ ...s, more: false, error: errorMessage(e) })) }
  }

  const set = (k, v) => { const p = new URLSearchParams(params); v ? p.set(k, v) : p.delete(k); setParams(p, { replace: true }) }

  return (
    <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6">
      <SectionTitle eyebrow="Matches" title="Find a match to catch up on">
        Historical matches come from Cricsheet ball-by-ball data. Demo matches replay a real match from a mid-way point so you can try the catch-up experience.
      </SectionTitle>

      <form onSubmit={(e) => { e.preventDefault(); set('q', draft.trim()) }} className="mb-5 flex flex-col gap-3 sm:flex-row">
        <label className="relative flex-1">
          <span className="sr-only">Search matches</span>
          <Search size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-mute" />
          <input value={draft} onChange={(e) => setDraft(e.target.value)} placeholder="Search team, venue, tournament or city"
            className="w-full rounded-xl border border-line bg-surface py-3 pl-10 pr-10 text-sm outline-none transition focus:border-accent" />
          {draft && <button type="button" onClick={() => { setDraft(''); set('q', '') }} className="absolute right-3 top-1/2 -translate-y-1/2 text-mute hover:text-ink" aria-label="Clear search"><X size={16} /></button>}
        </label>
        <button className="btn btn-primary" type="submit">Search</button>
      </form>

      <div className="mb-6 space-y-3">
        <div className="flex flex-wrap gap-2" role="tablist" aria-label="Category">
          {CATS.map(([v, l]) => <button key={v} role="tab" aria-selected={category === v} onClick={() => set('category', v === 'all' ? '' : v)} className={`chip ${category === v ? 'chip-on' : ''}`}>{l}</button>)}
        </div>
        <div className="flex flex-wrap gap-2">
          {FORMATS.map(([v, l]) => <button key={v} onClick={() => set('format', v)} className={`chip ${format === v ? 'chip-on' : ''}`}>{l}</button>)}
          <span className="mx-1 hidden w-px bg-line sm:block" />
          {GENDERS.map(([v, l]) => <button key={v} onClick={() => set('gender', v)} className={`chip ${gender === v ? 'chip-on' : ''}`}>{l}</button>)}
        </div>
      </div>

      {state.loading && <Loading rows={3} />}
      {state.error && <ErrorBox message={state.error} onRetry={() => set('_r', String(Date.now()))} />}
      {!state.loading && !state.error && state.items.length === 0 && (
        <Empty title={q ? `No matches for "${q}"` : `No ${category === 'all' ? '' : category + ' '}matches`}>
          {state.notice || 'Try clearing the filters.'}
          {(category === 'live' || category === 'upcoming') && <div className="mt-4"><Link to="/matches?category=demo" className="btn btn-primary">Try a demo match</Link></div>}
        </Empty>
      )}
      {state.notice && state.items.length > 0 && <Notice className="mb-4">{state.notice}</Notice>}
      {state.items.length > 0 && (
        <>
          <p className="mb-3 text-sm text-mute" aria-live="polite">{state.total} match{state.total === 1 ? '' : 'es'}</p>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{state.items.map((m) => <MatchCard key={m.id} match={m} />)}</div>
          {state.items.length < state.total && (
            <div className="mt-8 text-center">
              <button onClick={loadMore} disabled={state.more} className="btn btn-ghost">{state.more ? <Spinner /> : null} Load more</button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
