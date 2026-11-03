import { api, http } from './api'

/** Load everything a stream-style screen needs for one demo/highlights match id: ball records + key events. */
export async function loadStream(id) {
  const details = await api.match(id)
  const max = details.replay.max_seq
  const balls = []
  for (let off = 0; off <= max; off += 500) {
    const page = await http.get(`/api/matches/${id}/ball-by-ball`, { params: { at: max, limit: 500, offset: off } })
    balls.push(...page.data.items)
    if (balls.length >= page.data.total) break
  }
  const tl = await api.timeline(id, max)
  const toastTypes = ['wicket', 'six', 'big_over', 'innings_break']
  const events = tl.events.filter((e) => toastTypes.includes(e.type) || (e.type === 'milestone' && !e.superseded))
  // moments a highlights reel typically shows
  const moments = tl.events.filter((e) => ['wicket', 'six', 'four'].includes(e.type) || (e.type === 'milestone' && !e.superseded))
  const bySeq = new Map()
  events.forEach((e) => bySeq.set(e.seq, [...(bySeq.get(e.seq) || []), e]))
  const cum = []; let cur = 0; let last = 0
  balls.forEach((b) => { if (b.innings_no !== cur) { cur = b.innings_no; last = 0 } if (b.legal) last++; cum.push(last) })
  const inn1 = balls.filter((b) => b.innings_no === 1)
  const end1 = inn1[inn1.length - 1]
  return {
    details, balls, events, moments, bySeq, cum, max,
    inn1Total: end1 ? end1.team_runs : 0, inn1Score: end1 ? `${end1.team_runs}/${end1.team_wkts}` : '', inn1Team: inn1[0]?.batting_team,
  }
}

/** Scoreboard numbers at ball index i, computed from the replayed records only. */
export function tickerAt(st, i, format) {
  const b = st.balls[i]
  const legal = st.cum[i]
  const runs = b.team_runs
  const t = { team: b.batting_team, score: `${runs}/${b.team_wkts}`, overs: `${Math.floor(legal / 6)}.${legal % 6}`, innings: b.innings_no, rr: legal ? (runs * 6 / legal).toFixed(2) : '-', status: '', rrr: null }
  if (b.innings_no === 2 && format !== 'TEST') {
    const target = st.inn1Total + 1
    const left = (format === 'T20' ? 120 : 300) - legal
    const need = target - runs
    if (i >= st.balls.length - 1 && need <= 0) t.status = `${b.batting_team} reached the target`
    else if (need > 0 && left > 0) { t.rrr = (need * 6 / left).toFixed(2); t.status = `Need ${need} from ${left} balls` }
    else if (need > 0) t.status = `${b.batting_team} fell short by ${need}`
    t.target = target
  } else if (b.innings_no === 1) t.status = `${b.batting_team} batting first`
  return t
}

/** Highlights sync: which key moment is on screen at video time `t`? Pins (user-set) win over the even auto-spread. */
export function momentAt(moments, duration, t, pins) {
  if (pins.length) {
    const sorted = [...pins].sort((a, b) => a.t - b.t)
    let hit = -1
    sorted.forEach((p, i) => { if (p.t <= t) hit = i })
    return hit < 0 ? null : { seq: sorted[hit].seq, index: hit, pinned: true }
  }
  if (!moments.length || !duration) return null
  const idx = Math.min(moments.length - 1, Math.floor((t / duration) * moments.length))
  return { seq: moments[idx].seq, index: idx, pinned: false }
}
