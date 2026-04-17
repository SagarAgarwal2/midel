import { useState } from 'react'
import api from '../services/api'

export default function ChatPage() {
  const [messages, setMessages] = useState([
    { role: 'assistant', content: 'Ask me anything about supplier failures, delays, or risk mitigation.' },
  ])
  const [plan, setPlan] = useState(null)
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)

  const send = async () => {
    if (!input.trim()) return
    const userMessage = { role: 'user', content: input }
    setMessages((prev) => [...prev, userMessage])
    setInput('')
    setLoading(true)

    try {
      const { data } = await api.post('/chat', { message: userMessage.content })
      setMessages((prev) => [...prev, { role: 'assistant', content: data.response }])
      setPlan(data.mitigation_plan || null)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex h-[75vh] flex-col gap-4">
      <h2 className="font-display text-3xl tracking-tight">LLM Chat Assistant</h2>

      <div className="flex-1 space-y-3 overflow-y-auto rounded-2xl border border-slate-200 bg-white p-4">
        {messages.map((msg, idx) => (
          <div key={idx} className={`max-w-[80%] rounded-2xl p-3 text-sm ${msg.role === 'user' ? 'ml-auto bg-slate-900 text-white' : 'bg-slate-100 text-slate-700'}`}>
            {msg.content}
          </div>
        ))}
      </div>

      <div className="flex gap-3">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && send()}
          className="flex-1 rounded-xl border border-slate-300 px-3 py-2"
          placeholder="What should I do if supplier fails?"
        />
        <button onClick={send} disabled={loading} className="rounded-xl bg-cyan-600 px-4 py-2 text-white hover:bg-cyan-500">
          {loading ? 'Sending...' : 'Send'}
        </button>
      </div>

      {plan && (
        <section className="rounded-2xl border border-cyan-200 bg-cyan-50 p-4 text-sm text-cyan-950">
          <p className="font-display text-lg">Instant Cascade + Mitigation Plan</p>
          <p className="mt-1 font-semibold">{plan.impact?.headline}</p>
          <p className="mt-1">PO Top-up: {plan.po_top_up?.top_up_percentage}% ({plan.po_top_up?.urgency})</p>
          <p className="mt-2 whitespace-pre-wrap rounded-xl bg-white p-3">{plan.email_draft}</p>
          <p className="mt-2 text-xs">Reason codes: {(plan.reason_codes || []).join(', ')}</p>
        </section>
      )}
    </div>
  )
}
