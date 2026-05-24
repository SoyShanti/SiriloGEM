import { NavLink } from 'react-router-dom'
import { Music, Sparkles, Search, BarChart3, Settings } from 'lucide-react'
import { useApp } from '../context/AppContext'
import { motion } from 'framer-motion'

const links = [
  { to: '/', icon: Sparkles, label: 'Generate' },
  { to: '/discover', icon: Search, label: 'Discover' },
  { to: '/predict', icon: BarChart3, label: 'Predict' },
  { to: '/settings', icon: Settings, label: 'Settings' },
]

export function Layout({ children }: { children: React.ReactNode }) {
  const { status } = useApp()

  return (
    <div className="min-h-screen flex flex-col bg-surface">
      <header className="sticky top-0 z-50 glass border-b border-border-subtle">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          <NavLink to="/" className="flex items-center gap-2.5 group">
            <motion.div
              whileHover={{ rotate: 180 }}
              transition={{ duration: 0.4 }}
              className="w-9 h-9 rounded-xl bg-gradient-to-br from-gem-500 to-gem-700 flex items-center justify-center shadow-lg shadow-gem-500/20"
            >
              <Music className="w-5 h-5 text-white" />
            </motion.div>
            <span className="text-xl font-bold tracking-tight gradient-text">SpotiGem</span>
          </NavLink>

          <nav className="flex items-center gap-1">
            {links.map(({ to, icon: Icon, label }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  `flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
                    isActive
                      ? 'bg-gem-500/15 text-gem-300 shadow-sm'
                      : 'text-zinc-400 hover:text-zinc-200 hover:bg-surface-hover'
                  }`
                }
              >
                <Icon className="w-4 h-4" />
                <span className="hidden sm:inline">{label}</span>
              </NavLink>
            ))}
          </nav>

          <div className="flex items-center gap-2">
            <StatusDot available={status?.ace_step?.loaded} label="ACE Step" />
            <StatusDot available={status?.lm_studio?.available} label="LM Studio" />
          </div>
        </div>
      </header>

      <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 py-8">
        {children}
      </main>

      <footer className="border-t border-border-subtle py-6 text-center text-xs text-zinc-500">
        SpotiGem — AI Music Hit Generator powered by ACE Step & Spotify Data
      </footer>
    </div>
  )
}

function StatusDot({ available, label }: { available?: boolean; label: string }) {
  return (
    <div className="flex items-center gap-1.5 text-xs" title={`${label}: ${available ? 'Online' : 'Offline'}`}>
      <div className={`w-2 h-2 rounded-full ${available ? 'bg-emerald-400 shadow-sm shadow-emerald-400/50' : 'bg-zinc-600'}`} />
      <span className="hidden md:inline text-zinc-500">{label}</span>
    </div>
  )
}
