import { useState } from 'react'
import { Link, NavLink, useNavigate } from 'react-router-dom'
import { Menu, Moon, Search, Sun, X } from 'lucide-react'
import Logo from './Logo'
import { useTheme } from '../lib/theme'

const NAV = [
  { to: '/', label: 'Home', end: true },
  { to: '/matches', label: 'Matches' },
  { to: '/insights', label: 'Match Insights' },
  { to: '/live-demo', label: 'Live Stream Demo' },
  { to: '/about', label: 'About' },
]

export default function Header() {
  const { theme, toggle } = useTheme()
  const [open, setOpen] = useState(false)
  const [searching, setSearching] = useState(false)
  const [q, setQ] = useState('')
  const nav = useNavigate()

  const submit = (e) => {
    e.preventDefault()
    nav(`/matches?q=${encodeURIComponent(q.trim())}`)
    setSearching(false); setOpen(false)
  }
  const link = ({ isActive }) =>
    `rounded-lg px-3 py-2 text-sm font-medium transition ${isActive ? 'bg-accent/15 text-accent' : 'text-mute hover:text-ink'}`

  return (
    <header className="sticky top-0 z-40 border-b border-line/70 bg-bg/80 backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-7xl items-center gap-3 px-4 sm:px-6">
        <Link to="/" aria-label="MatchBack AI home"><Logo /></Link>
        <nav className="ml-6 hidden items-center gap-1 md:flex" aria-label="Main">
          {NAV.map((n) => <NavLink key={n.to} {...n} className={link}>{n.label}</NavLink>)}
        </nav>
        <div className="ml-auto flex items-center gap-2">
          {searching ? (
            <form onSubmit={submit} className="flex items-center gap-2">
              <input autoFocus value={q} onChange={(e) => setQ(e.target.value)} placeholder="Team, venue, tournament..."
                aria-label="Search matches" className="w-40 rounded-xl border border-line bg-surface px-3 py-2 text-sm outline-none focus:border-accent sm:w-64" />
              <button type="button" onClick={() => setSearching(false)} className="btn btn-ghost !p-2" aria-label="Close search"><X size={16} /></button>
            </form>
          ) : (
            <button onClick={() => setSearching(true)} className="btn btn-ghost !p-2.5" aria-label="Search matches"><Search size={16} /></button>
          )}
          <button onClick={toggle} className="btn btn-ghost !p-2.5" aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}>
            {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
          </button>
          <button onClick={() => setOpen((o) => !o)} className="btn btn-ghost !p-2.5 md:hidden" aria-label="Menu" aria-expanded={open}>
            {open ? <X size={16} /> : <Menu size={16} />}
          </button>
        </div>
      </div>
      {open && (
        <nav className="border-t border-line bg-bg px-4 py-3 md:hidden" aria-label="Mobile">
          <div className="flex flex-col gap-1">
            {NAV.map((n) => <NavLink key={n.to} {...n} className={link} onClick={() => setOpen(false)}>{n.label}</NavLink>)}
          </div>
        </nav>
      )}
    </header>
  )
}
