import { Link } from 'react-router-dom'
import Logo from './Logo'

export default function Footer() {
  return (
    <footer className="mt-24 border-t border-line">
      <div className="mx-auto flex max-w-7xl flex-col gap-6 px-4 py-10 sm:px-6 md:flex-row md:items-start md:justify-between">
        <div className="max-w-sm">
          <Logo />
          <p className="mt-3 text-sm text-mute">Missed the match? Catch up in 30 seconds.</p>
          <p className="mt-3 text-xs text-mute">
            Independent prototype built for a Forward Deployed Engineer internship assignment. Not affiliated with any fantasy-sports
            operator, league or board. No third-party logos or flags are used.
          </p>
        </div>
        <div className="grid grid-cols-2 gap-8 text-sm">
          <div className="flex flex-col gap-2">
            <span className="label">Explore</span>
            <Link to="/matches" className="text-mute hover:text-ink">Matches</Link>
            <Link to="/insights" className="text-mute hover:text-ink">Match Insights</Link>
            <Link to="/about" className="text-mute hover:text-ink">About &amp; data</Link>
          </div>
          <div className="flex flex-col gap-2">
            <span className="label">Data</span>
            <a href="https://cricsheet.org/" target="_blank" rel="noreferrer" className="text-mute hover:text-ink">Ball-by-ball data: Cricsheet</a>
            <span className="text-mute">AI: local open-source models via Ollama (optional)</span>
          </div>
        </div>
      </div>
    </footer>
  )
}
