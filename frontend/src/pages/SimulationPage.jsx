import { useState } from 'react'
import api from '../services/api'

const INITIAL = {
  supplier: 'Nova Sourcing',
  demand_per_day: 140,
  inventory: 220,
  delay_days: 6,
  product_price: 22,
  supplier_reliability: 0.82,
}

export default function SimulationPage() {
  const [form, setForm] = useState(INITIAL)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const onChange = (key, value) => {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  const runSimulation = async () => {
    setLoading(true)
    try {
      setError('')
      const { data } = await api.post('/decision', {
        ...form,
        explain: true,
        alternative_suppliers: [
          { name: 'AltFast', cost: 1.1, delay: Math.max(1, Number(form.delay_days) - 2), reliability: 0.9, capacity: 0.7 },
          { name: 'AltBudget', cost: 0.93, delay: Number(form.delay_days) + 1, reliability: 0.72, capacity: 1.0 },
        ],
      })
      setResult(data)
    } catch (err) {
      const message = err?.response?.data?.error || err?.message || 'Unable to run simulation.'
      setError(message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      {error && <p className="rounded-xl bg-rose-100 p-3 text-sm text-rose-700">Backend error: {error}</p>}
      <h2 className="font-display text-3xl tracking-tight">Scenario Simulation</h2>

      <section className="grid gap-4 rounded-2xl border border-slate-200 bg-white p-4 md:grid-cols-3">
        {[
          ['demand_per_day', 'Demand / day'],
          ['inventory', 'Inventory'],
          ['delay_days', 'Delay (days)'],
          ['product_price', 'Product price'],
          ['supplier_reliability', 'Supplier reliability (0-1)'],
        ].map(([key, label]) => (
          <label key={key} className="space-y-2 text-sm text-slate-600">
            <span>{label}</span>
            <input
              value={form[key]}
              onChange={(e) => onChange(key, e.target.value)}
              className="w-full rounded-xl border border-slate-300 px-3 py-2"
              type="number"
              step="0.01"
            />
          </label>
        ))}
      </section>

      <button onClick={runSimulation} className="rounded-xl bg-slate-900 px-4 py-2 text-white hover:bg-slate-700">
        {loading ? 'Running simulation...' : 'Run Decision Engine'}
      </button>

      {result && (
        <section className="space-y-4 rounded-2xl border border-slate-200 bg-white p-4">
          <p className="font-display text-xl">Best decision: {result.best_option.option}</p>
          <p className="text-sm text-slate-600">Savings: ${result.savings} | Confidence: {result.confidence_score}</p>
          <p className="rounded-xl bg-cyan-50 p-3 text-sm text-cyan-900">{result.explanation}</p>

          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-slate-50 text-left">
                <tr>
                  <th className="px-3 py-2">Option</th>
                  <th className="px-3 py-2">Revenue Loss</th>
                  <th className="px-3 py-2">Extra Cost</th>
                  <th className="px-3 py-2">Delay</th>
                  <th className="px-3 py-2">Score</th>
                </tr>
              </thead>
              <tbody>
                {result.options.map((option) => (
                  <tr key={option.option} className="border-t border-slate-100">
                    <td className="px-3 py-2">{option.option}</td>
                    <td className="px-3 py-2">{option.revenue_loss}</td>
                    <td className="px-3 py-2">{option.extra_cost}</td>
                    <td className="px-3 py-2">{option.delay}</td>
                    <td className="px-3 py-2">{option.score}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  )
}
