import { useState } from 'react'
import api from '../services/api'

export default function ImpactPage() {
  const [records, setRecords] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const runImpact = async () => {
    setLoading(true)
    try {
      setError('')
      const { data } = await api.post('/impact', {})
      setRecords(data.records || [])
      setTotal(data.total_revenue_loss || 0)
    } catch (err) {
      const message = err?.response?.data?.error || err?.message || 'Unable to calculate impact.'
      setError(message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      {error && <p className="rounded-xl bg-rose-100 p-3 text-sm text-rose-700">Backend error: {error}</p>}
      <h2 className="font-display text-3xl tracking-tight">Impact Analysis</h2>
      <div className="flex items-center gap-3">
        <button onClick={runImpact} className="rounded-xl bg-slate-900 px-4 py-2 text-white hover:bg-slate-700">
          {loading ? 'Calculating...' : 'Calculate Financial Impact'}
        </button>
        <span className="rounded-xl bg-rose-100 px-4 py-2 text-rose-700">Total Revenue Loss: ${total.toLocaleString()}</span>
      </div>

      <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-50 text-left text-slate-600">
            <tr>
              <th className="px-4 py-3">Product</th>
              <th className="px-4 py-3">Stockout Days</th>
              <th className="px-4 py-3">Revenue Loss</th>
            </tr>
          </thead>
          <tbody>
            {records.map((row, idx) => (
              <tr key={idx} className="border-t border-slate-100">
                <td className="px-4 py-3">{row.product || 'unknown'}</td>
                <td className="px-4 py-3">{row.stockout_days}</td>
                <td className="px-4 py-3">${row.revenue_loss}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
