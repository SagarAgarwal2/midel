import { useState } from 'react'
import api from '../services/api'

export default function RisksPage() {
  const [records, setRecords] = useState([])
  const [alerts, setAlerts] = useState([])
  const [agentRuns, setAgentRuns] = useState([])
  const [loading, setLoading] = useState(false)
  const [threshold, setThreshold] = useState(70)

  const runRiskDetection = async () => {
    setLoading(true)
    try {
      await api.post('/signals/poll')
      const { data } = await api.post('/risk/refresh', { threshold })
      setRecords(data.scores || [])
      setAlerts(data.alerts || [])
    } finally {
      setLoading(false)
    }
  }

  const runAgentLoop = async () => {
    setLoading(true)
    try {
      const { data } = await api.post('/agent/run', { threshold })
      setAgentRuns(data.workflows || [])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <h2 className="font-display text-3xl tracking-tight">Risk Detection Engine (15-minute cycle)</h2>
      <div className="flex items-center gap-3">
        <input
          type="number"
          className="w-36 rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm"
          value={threshold}
          onChange={(e) => setThreshold(Number(e.target.value))}
          min={1}
          max={100}
        />
        <button onClick={runRiskDetection} className="rounded-xl bg-slate-900 px-4 py-2 text-white hover:bg-slate-700">
          {loading ? 'Analyzing...' : 'Refresh Risk Scores'}
        </button>
        <button onClick={runAgentLoop} className="rounded-xl bg-cyan-700 px-4 py-2 text-white hover:bg-cyan-600">
          {loading ? 'Running...' : 'Run Agentic Response'}
        </button>
      </div>

      <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-slate-50 text-slate-600">
            <tr>
              <th className="px-4 py-3">Supplier</th>
              <th className="px-4 py-3">Risk Score</th>
              <th className="px-4 py-3">On-time Rate</th>
              <th className="px-4 py-3">Geo Risk</th>
              <th className="px-4 py-3">Reason Codes</th>
            </tr>
          </thead>
          <tbody>
            {records.map((row, idx) => (
              <tr key={idx} className="border-t border-slate-100">
                <td className="px-4 py-3">{row.supplier || 'unknown'}</td>
                <td className="px-4 py-3">{row.risk_score}</td>
                <td className="px-4 py-3">{row.historical_on_time_rate}</td>
                <td className="px-4 py-3">{row.geo_concentration_risk}</td>
                <td className="px-4 py-3">
                  <span
                    className={`rounded-full px-3 py-1 text-xs ${
                      row.risk_band === 'Critical' || row.risk_band === 'High'
                        ? 'bg-rose-100 text-rose-700'
                        : row.risk_band === 'Medium'
                          ? 'bg-amber-100 text-amber-700'
                          : 'bg-emerald-100 text-emerald-700'
                    }`}
                  >
                    {(row.reason_codes || []).join(', ')}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <section className="grid gap-4 lg:grid-cols-2">
        <article className="rounded-2xl border border-slate-200 bg-white p-4">
          <h3 className="mb-3 font-display text-xl">Threshold Alerts</h3>
          <div className="space-y-2 text-sm">
            {alerts.length === 0 && <p className="text-slate-500">No alerts at current threshold.</p>}
            {alerts.map((alert, idx) => (
              <div key={`${alert.supplier}-${idx}`} className="rounded-xl bg-rose-50 p-3 text-rose-800">
                <p className="font-semibold">{alert.supplier}: {alert.risk_score}</p>
                <p>{alert.reason}</p>
              </div>
            ))}
          </div>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-4">
          <h3 className="mb-3 font-display text-xl">Agentic Loop Output</h3>
          <div className="space-y-2 text-sm">
            {agentRuns.length === 0 && <p className="text-slate-500">Run the agentic response to view drafts.</p>}
            {agentRuns.map((run, idx) => (
              <div key={`${run.supplier}-${idx}`} className="rounded-xl bg-cyan-50 p-3 text-cyan-900">
                <p className="font-semibold">{run.supplier}</p>
                <p>{run.analyst?.report?.headline}</p>
                <p className="mt-1 text-xs">Reason codes: {(run.detector?.reason_codes || []).join(', ')}</p>
              </div>
            ))}
          </div>
        </article>
      </section>
    </div>
  )
}
