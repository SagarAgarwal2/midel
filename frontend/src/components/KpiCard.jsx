export default function KpiCard({ label, value, tone = 'default' }) {
  const tones = {
    default: 'from-slate-900 to-slate-700 text-white',
    warning: 'from-amber-500 to-orange-500 text-white',
    danger: 'from-rose-500 to-pink-500 text-white',
    cool: 'from-cyan-500 to-blue-500 text-white',
  }

  return (
    <div className={`rounded-2xl bg-gradient-to-br p-5 shadow-lg ${tones[tone] || tones.default}`}>
      <p className="text-sm opacity-90">{label}</p>
      <p className="mt-4 font-display text-3xl tracking-tight">{value}</p>
    </div>
  )
}
