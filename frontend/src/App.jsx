import { lazy, Suspense, useEffect } from 'react'
import { Route, Routes, useLocation } from 'react-router-dom'
import Header from './components/Header'
import Footer from './components/Footer'
import { Loading } from './components/ui'
import Home from './pages/Home'
import Matches from './pages/Matches'
import Insights from './pages/Insights'
import About from './pages/About'
import NotFound from './pages/NotFound'
import MatchDetail from './pages/MatchDetail'
const LiveDemo = lazy(() => import('./pages/LiveDemo'))

// Chart-heavy tabs are code-split so the landing page stays light.
const Overview = lazy(() => import('./pages/match/Overview'))
const CatchUp = lazy(() => import('./pages/match/CatchUp'))
const Timeline = lazy(() => import('./pages/match/Timeline'))
const Scorecard = lazy(() => import('./pages/match/Scorecard'))
const Players = lazy(() => import('./pages/match/Players'))
const Milestones = lazy(() => import('./pages/match/Milestones'))
const Momentum = lazy(() => import('./pages/match/Momentum'))

function ScrollTop() {
  const { pathname } = useLocation()
  useEffect(() => { if (!pathname.startsWith('/match/')) window.scrollTo(0, 0) }, [pathname])
  return null
}

export default function App() {
  const { pathname } = useLocation()
  const bare = /^\/live/.test(pathname)  // the stream prototype brings its own app bar
  return (
    <div className="flex min-h-screen flex-col">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-accent focus:px-3 focus:py-2 focus:text-accent-ink">Skip to content</a>
      {!bare && <Header />}
      <ScrollTop />
      <main id="main" className="flex-1">
        <Suspense fallback={<div className="mx-auto max-w-7xl px-4 py-10"><Loading /></div>}>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/matches" element={<Matches />} />
            <Route path="/insights" element={<Insights />} />
            <Route path="/about" element={<About />} />
            <Route path="/live-demo" element={<LiveDemo />} />
            <Route path="/match/:id" element={<MatchDetail />}>
              <Route index element={<Overview />} />
              <Route path="catch-up" element={<CatchUp />} />
              <Route path="timeline" element={<Timeline />} />
              <Route path="scorecard" element={<Scorecard />} />
              <Route path="players" element={<Players />} />
              <Route path="milestones" element={<Milestones />} />
              <Route path="momentum" element={<Momentum />} />
            </Route>
            <Route path="*" element={<NotFound />} />
          </Routes>
        </Suspense>
      </main>
      {!bare && <Footer />}
    </div>
  )
}
