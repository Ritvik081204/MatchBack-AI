import { Link } from 'react-router-dom'
import { Empty } from '../components/ui'

export default function NotFound() {
  return (
    <div className="mx-auto max-w-xl px-4 py-24">
      <Empty title="That page is out of the ground">The link you followed doesn't exist.<div className="mt-4"><Link className="btn btn-primary" to="/">Back to home</Link></div></Empty>
    </div>
  )
}
