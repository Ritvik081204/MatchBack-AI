import { useCallback, useEffect, useRef, useState } from 'react'
import { errorMessage } from './api'

/** Fetch on mount / when deps change. Ignores stale responses. */
export function useApi(fn, deps = []) {
  const [state, setState] = useState({ data: null, loading: true, error: null })
  const seq = useRef(0)
  const run = useCallback(() => {
    const id = ++seq.current
    setState((s) => ({ ...s, loading: true, error: null }))
    Promise.resolve()
      .then(fn)
      .then((data) => id === seq.current && setState({ data, loading: false, error: null }))
      .catch((e) => id === seq.current && setState({ data: null, loading: false, error: errorMessage(e) }))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)
  useEffect(() => {
    run()
    return () => { seq.current++ }
  }, [run])
  return { ...state, reload: run }
}

export function useLocalStorage(key, initial) {
  const [value, setValue] = useState(() => {
    try { const v = localStorage.getItem(key); return v === null ? initial : JSON.parse(v) } catch { return initial }
  })
  useEffect(() => {
    try { localStorage.setItem(key, JSON.stringify(value)) } catch { /* storage may be blocked */ }
  }, [key, value])
  return [value, setValue]
}
