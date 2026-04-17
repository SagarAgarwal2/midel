import { useEffect, useMemo, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  PieChart,
  Pie,
  Cell,
} from 'recharts'

import KpiCard from '../components/KpiCard'
import api from '../services/api'

const PIE_COLORS = ['#22c55e', '#f59e0b', '#ef4444']

export default function DashboardPage() {
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(true)
  const [simForm, setSimForm] = useState({ supplier: '', severity: 0.8, duration_days: 5 })
  const [simResult, setSimResult] = useState(null)
  const [simLoading, setSimLoading] = useState(false)

  useEffect(() => {
    const load = async () => {
      try {
        await api.post('/signals/poll')
        await api.get('/risk/supplier-scores')
        const { data } = await api.get('/summary')
        setSummary(data)
        const firstSupplier = data?.supplier_heatmap?.[0]?.supplier || ''
        setSimForm((prev) => ({ ...prev, supplier: firstSupplier }))
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  const riskData = useMemo(() => {
    if (!summary) return []
    return Object.entries(summary.risk_distribution).map(([name, value]) => ({ name, value }))
  }, [summary])

  const runWhatIf = async () => {
    if (!simForm.supplier) return
    setSimLoading(true)
    try {
      const { data } = await api.post('/simulate/what-if', simForm)
      setSimResult(data)
    } finally {
      setSimLoading(false)
    }
  }

  if (loading) {
    return <p className="text-slate-500">Loading dashboard...</p>
  }

  const kpis = summary?.kpis || {
    total_products: 0,
    active_risks: 0,
    estimated_revenue_loss: 0,
    delayed_shipments: 0,
  }

  return (
    <div className="space-y-8">
      <div>
        <h2 className="font-display text-3xl tracking-tight">Control Tower Dashboard</h2>
        <p className="mt-2 text-slate-500">Unified resilience view across suppliers, demand, and decisions.</p>
      </div>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <KpiCard label="Total Products" value={kpis.total_products} tone="cool" />
        <KpiCard label="Active Risks" value={kpis.active_risks} tone="warning" />
        <KpiCard label="Estimated Revenue Loss" value={`$${kpis.estimated_revenue_loss.toLocaleString()}`} tone="danger" />
        <KpiCard label="Delayed Shipments" value={kpis.delayed_shipments} tone="default" />
      </section>

      <section className="grid gap-5 lg:grid-cols-2">
        <article className="rounded-2xl border border-slate-200 bg-white p-4">
          <h3 className="mb-4 font-display text-xl">Risk Distribution</h3>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={riskData} dataKey="value" nameKey="name" outerRadius={110}>
                  {riskData.map((_, i) => (
                    <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-4">
          <h3 className="mb-4 font-display text-xl">Inventory vs Demand</h3>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={summary?.inventory_vs_demand || []}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="product" hide />
                <YAxis />
                <Tooltip />
                <Legend />
                <Bar dataKey="inventory" fill="#0ea5e9" radius={[8, 8, 0, 0]} />
                <Bar dataKey="demand" fill="#f97316" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </article>
      </section>

      <section className="grid gap-5 lg:grid-cols-3">
        <article className="rounded-2xl border border-slate-200 bg-white p-4 lg:col-span-2">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="font-display text-xl">Supplier Heatmap (0-100)</h3>
            <span className="text-xs text-slate-500">Auto refresh every 15 min</span>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {(summary?.supplier_heatmap || []).map((item) => {
              const tone =
                item.risk_score >= 80
                  ? 'bg-rose-100 text-rose-800'
                  : item.risk_score >= 60
                    ? 'bg-amber-100 text-amber-800'
                    : 'bg-emerald-100 text-emerald-800'
              return (
                <button
                  key={item.supplier}
                  className={`rounded-xl px-3 py-3 text-left ${tone}`}
                  onClick={() => setSimForm((prev) => ({ ...prev, supplier: item.supplier }))}
                >
                  <p className="font-semibold">{item.supplier}</p>
                  <p className="text-sm">Risk: {item.risk_score}</p>
                  <p className="mt-1 text-xs">{(item.reason_codes || []).join(', ')}</p>
                </button>
              )
            })}
          </div>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-4">
          <h3 className="mb-3 font-display text-xl">Alert Feed</h3>
          <div className="space-y-2">
            {(summary?.alerts || []).length === 0 && <p className="text-sm text-slate-500">No active alerts.</p>}
            {(summary?.alerts || []).map((alert, idx) => (
              <div key={`${alert.supplier}-${idx}`} className="rounded-xl border border-slate-100 bg-slate-50 p-3 text-sm">
                <p className="font-medium">{alert.supplier} • {alert.severity || 'info'}</p>
                <p className="text-slate-600">{alert.reason}</p>
                <p className="mt-1 text-xs text-slate-500">{(alert.reason_codes || []).join(', ')}</p>
              </div>
            ))}
          </div>
        </article>
      </section>

      <section className="grid gap-5 lg:grid-cols-2">
        <article className="rounded-2xl border border-slate-200 bg-white p-4">
          <h3 className="mb-4 font-display text-xl">Impact Simulation Panel</h3>
          <div className="space-y-3">
            <label className="block text-sm text-slate-600">
              Supplier
              <select
                value={simForm.supplier}
                onChange={(e) => setSimForm((prev) => ({ ...prev, supplier: e.target.value }))}
                className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2"
              >
                {(summary?.supplier_heatmap || []).map((item) => (
                  <option key={item.supplier} value={item.supplier}>{item.supplier}</option>
                ))}
              </select>
            </label>

            <label className="block text-sm text-slate-600">
              Disruption Severity: {Number(simForm.severity).toFixed(2)}
              <input
                type="range"
                min="0.1"
                max="1"
                step="0.05"
                value={simForm.severity}
                onChange={(e) => setSimForm((prev) => ({ ...prev, severity: Number(e.target.value) }))}
                className="mt-2 w-full"
              />
            </label>

            <label className="block text-sm text-slate-600">
              Duration (days): {simForm.duration_days}
              <input
                type="range"
                min="1"
                max="14"
                step="1"
                value={simForm.duration_days}
                onChange={(e) => setSimForm((prev) => ({ ...prev, duration_days: Number(e.target.value) }))}
                className="mt-2 w-full"
              />
            </label>

            <button onClick={runWhatIf} className="rounded-xl bg-slate-900 px-4 py-2 text-white hover:bg-slate-700">
              {simLoading ? 'Simulating...' : 'Drag & Simulate'}
            </button>
          </div>

          {simResult && (
            <div className="mt-4 rounded-xl bg-amber-50 p-3 text-sm text-amber-900">
              <p className="font-semibold">{simResult.headline}</p>
              <p className="mt-1">Revenue at risk: INR {Number(simResult.total_revenue_at_risk_inr || 0).toLocaleString()}</p>
            </div>
          )}
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-4">
          <h3 className="mb-4 font-display text-xl">Festival / Holiday Calendar</h3>
          <div className="space-y-2 text-sm">
            {(summary?.festival_calendar || []).map((event) => (
              <div key={`${event.date}-${event.festival}`} className="rounded-xl border border-slate-100 bg-slate-50 p-3">
                <p className="font-medium">{event.festival}</p>
                <p className="text-slate-600">{event.date}</p>
                <p className="text-xs text-slate-500">{event.risk_hint}</p>
              </div>
            ))}
          </div>
        </article>
      </section>
    </div>
  )
}
