import axios from 'axios'

// Same-origin in dev (Vite proxy) and when the API is served alongside; override for a separately hosted backend.
const http = axios.create({ baseURL: import.meta.env.VITE_API_URL || '', timeout: 45000 })

const at = (v) => (v === null || v === undefined ? {} : { at: v })

export const api = {
  health: () => http.get('/api/health').then((r) => r.data),
  matches: (params) => http.get('/api/matches', { params }).then((r) => r.data),
  match: (id, atSeq) => http.get(`/api/matches/${id}`, { params: at(atSeq) }).then((r) => r.data),
  scorecard: (id, atSeq) => http.get(`/api/matches/${id}/scorecard`, { params: at(atSeq) }).then((r) => r.data),
  timeline: (id, atSeq) => http.get(`/api/matches/${id}/timeline`, { params: at(atSeq) }).then((r) => r.data),
  statistics: (id, atSeq) => http.get(`/api/matches/${id}/statistics`, { params: at(atSeq) }).then((r) => r.data),
  milestones: (id, atSeq, includeSuperseded = false) =>
    http.get(`/api/matches/${id}/milestones`, { params: { ...at(atSeq), include_superseded: includeSuperseded } }).then((r) => r.data),
  turningPoints: (id, atSeq) => http.get(`/api/matches/${id}/turning-points`, { params: at(atSeq) }).then((r) => r.data),
  suggestions: (id, atSeq) => http.get(`/api/matches/${id}/suggestions`, { params: at(atSeq) }).then((r) => r.data),
  catchUp: (id, body) => http.post(`/api/matches/${id}/catch-up`, body).then((r) => r.data),
  ask: (id, body) => http.post(`/api/matches/${id}/ask`, body).then((r) => r.data),
  explain: (id, body) => http.post(`/api/matches/${id}/event-explanation`, body).then((r) => r.data),
}

export function errorMessage(err) {
  if (err?.response?.data?.detail) {
    const d = err.response.data.detail
    return typeof d === 'string' ? d : 'The request was not valid.'
  }
  if (err?.code === 'ECONNABORTED') return 'The server took too long to respond.'
  if (err?.message === 'Network Error') return 'Cannot reach the MatchBack AI server. Is the backend running on port 8000?'
  return err?.message || 'Something went wrong.'
}
