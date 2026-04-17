import { NavLink } from 'react-router-dom'
import { BarChart3, AlertTriangle, TrendingDown, FlaskConical, Upload, MessageSquare } from 'lucide-react'

const NAV_ITEMS = [
  { to: '/', label: 'Dashboard', icon: BarChart3 },
  { to: '/risks', label: 'Risks', icon: AlertTriangle },
  { to: '/impact', label: 'Impact', icon: TrendingDown },
  { to: '/simulation', label: 'Simulation', icon: FlaskConical },
  { to: '/upload', label: 'Upload', icon: Upload },
  { to: '/chat', label: 'Chat Assistant', icon: MessageSquare },
]

export default function Layout({ children }) {
  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_10%_20%,#ecfeff,transparent_45%),radial-gradient(circle_at_90%_10%,#fef3c7,transparent_30%),linear-gradient(165deg,#f8fafc,#eef2ff)] text-slate-800">
      <div className="mx-auto flex w-full max-w-[1400px] gap-6 p-4 md:p-8">
        <aside className="sticky top-4 hidden h-[calc(100vh-2rem)] w-72 shrink-0 rounded-3xl border border-white/50 bg-white/70 p-5 backdrop-blur-xl md:block">
          <h1 className="font-display text-2xl tracking-tight">PulseChain IQ</h1>
          <p className="mt-2 text-sm text-slate-500">Resilience & Decision Intelligence</p>
          <nav className="mt-8 space-y-2">
            {NAV_ITEMS.map((item) => {
              const Icon = item.icon
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={({ isActive }) =>
                    `flex items-center gap-3 rounded-xl px-4 py-3 text-sm transition ${
                      isActive
                        ? 'bg-slate-900 text-white shadow-lg shadow-slate-900/25'
                        : 'text-slate-600 hover:bg-white hover:text-slate-900'
                    }`
                  }
                >
                  <Icon size={18} />
                  {item.label}
                </NavLink>
              )
            })}
          </nav>
        </aside>

        <main className="w-full rounded-3xl border border-white/60 bg-white/65 p-4 shadow-xl shadow-slate-200/40 backdrop-blur-xl md:p-8">
          {children}
        </main>
      </div>
    </div>
  )
}
