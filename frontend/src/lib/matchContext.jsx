import { createContext, useContext } from 'react'
import { useOutletContext } from 'react-router-dom'

/** Lets the match tabs run either as routed pages (Outlet context) or embedded in another screen (provider). */
export const MatchCtx = createContext(null)

export function useMatchCtx() {
  const outlet = useOutletContext()
  const provided = useContext(MatchCtx)
  return provided || outlet
}
