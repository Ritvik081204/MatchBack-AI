import { useState } from 'react'
import { ErrorBox, Loading } from '../../components/ui'
import { useMatchCtx } from '../../lib/matchContext'
import { api } from '../../lib/api'
import { useApi } from '../../lib/hooks'

function Th({ children, className = '' }) { return <th className={`px-3 py-2 text-right text-[11px] font-semibold uppercase tracking-wider text-mute first:text-left ${className}`}>{children}</th> }
function Td({ children, className = '' }) { return <td className={`num px-3 py-2.5 text-right first:text-left ${className}`}>{children}</td> }

export default function Scorecard() {
  const { id, at } = useMatchCtx()
  const { data, loading, error, reload } = useApi(() => api.scorecard(id, at), [id, at])
  const [sel, setSel] = useState(null)
  if (loading && !data) return <Loading rows={3} />
  if (error) return <ErrorBox message={error} onRetry={reload} />
  const innings = data.innings
  const n = sel ?? innings[innings.length - 1].innings_no
  const card = innings.find((i) => i.innings_no === n)

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap gap-2" role="tablist" aria-label="Innings">
        {innings.map((i) => (
          <button key={i.innings_no} role="tab" aria-selected={n === i.innings_no} onClick={() => setSel(i.innings_no)} className={`chip ${n === i.innings_no ? 'chip-on' : ''}`}>
            {i.innings_no}. {i.team} <span className="num font-bold">{i.total.runs}/{i.total.wickets}</span>
          </button>
        ))}
      </div>

      <section className="card overflow-hidden">
        <div className="flex flex-wrap items-baseline justify-between gap-2 border-b border-line px-4 py-3">
          <h3 className="font-display text-lg font-semibold">{card.team} batting</h3>
          <div className="num font-display text-xl font-bold">{card.total.runs}/{card.total.wickets} <span className="text-sm font-medium text-mute">({card.total.overs} ov · RR {card.total.run_rate ?? '-'})</span></div>
        </div>
        <div className="scroll-x">
          <table className="w-full min-w-[560px] text-sm">
            <thead><tr className="border-b border-line bg-surface2/40"><Th>Batter</Th><Th>Dismissal</Th><Th>R</Th><Th>B</Th><Th>4s</Th><Th>6s</Th><Th>SR</Th></tr></thead>
            <tbody>
              {card.batters.map((b) => (
                <tr key={b.name} className="border-b border-line/60 last:border-0">
                  <td className="px-3 py-2.5 font-semibold">{b.name}{!b.out && b.balls > 0 && <span className="text-accent">*</span>}</td>
                  <td className="px-3 py-2.5 text-right text-xs text-mute">{b.balls === 0 && !b.out ? 'yet to face' : b.dismissal}</td>
                  <Td className="font-bold">{b.runs}</Td><Td>{b.balls}</Td><Td>{b.fours}</Td><Td>{b.sixes}</Td><Td>{b.strike_rate ?? '-'}</Td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="space-y-1.5 border-t border-line px-4 py-3 text-sm">
          <div><span className="text-mute">Extras: </span><b className="num">{card.extras.total}</b> <span className="text-xs text-mute">(w {card.extras.wides}, nb {card.extras.noballs}, b {card.extras.byes}, lb {card.extras.legbyes}{card.extras.penalty ? `, pen ${card.extras.penalty}` : ''})</span></div>
          {card.yet_to_bat?.length > 0 && <div className="text-xs text-mute"><span className="font-semibold">{card.finished ? 'Did not bat' : 'Yet to bat'}:</span> {card.yet_to_bat.join(', ')}</div>}
          {card.fall_of_wickets.length > 0 && (
            <div className="text-xs text-mute"><span className="font-semibold">Fall of wickets:</span> {card.fall_of_wickets.map((f) => `${f.runs}-${f.wicket_no} (${f.player}, ${f.over} ov)`).join(', ')}</div>
          )}
        </div>
      </section>

      <section className="card overflow-hidden">
        <div className="border-b border-line px-4 py-3"><h3 className="font-display text-lg font-semibold">Bowling</h3></div>
        <div className="scroll-x">
          <table className="w-full min-w-[520px] text-sm">
            <thead><tr className="border-b border-line bg-surface2/40"><Th>Bowler</Th><Th>O</Th><Th>M</Th><Th>R</Th><Th>W</Th><Th>Econ</Th><Th>Dots</Th><Th>Wd/Nb</Th></tr></thead>
            <tbody>
              {card.bowling.map((b) => (
                <tr key={b.name} className="border-b border-line/60 last:border-0">
                  <td className="px-3 py-2.5 font-semibold">{b.name}</td><Td>{b.overs}</Td><Td>{b.maidens}</Td><Td>{b.runs}</Td>
                  <Td className="font-bold">{b.wickets}</Td><Td>{b.economy ?? '-'}</Td><Td>{b.dots}</Td><Td>{b.wides}/{b.noballs}</Td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="border-t border-line px-4 py-2.5 text-[11px] text-mute">Runs conceded count bat runs, wides and no-balls; byes, leg-byes and penalty runs are not charged to the bowler.</p>
      </section>
    </div>
  )
}
