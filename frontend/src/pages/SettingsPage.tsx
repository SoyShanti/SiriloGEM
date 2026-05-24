import { motion } from 'framer-motion'
import { RefreshCw, Database, Server, Brain, Music } from 'lucide-react'
import { useApp } from '../context/AppContext'
import { api } from '../lib/api'
import { useState } from 'react'

export function SettingsPage() {
  const { status, loading, refresh } = useApp()
  const [loadingAce, setLoadingAce] = useState(false)
  const [aceMsg, setAceMsg] = useState('')

  const handleLoadAce = async () => {
    setLoadingAce(true)
    setAceMsg('')
    try {
      const res = await api.loadAceStep()
      setAceMsg(`ACE Step loaded at ${res.api_url}`)
      refresh()
    } catch (e) {
      setAceMsg(e instanceof Error ? e.message : 'Failed to load ACE Step')
    } finally {
      setLoadingAce(false)
    }
  }

  return (
    <div className="space-y-8 max-w-3xl mx-auto">
      <div className="text-center space-y-2">
        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-4xl font-bold tracking-tight gradient-text"
        >
          Settings
        </motion.h1>
        <p className="text-zinc-400">System status and configuration</p>
      </div>

      <div className="space-y-4">
        <Card icon={<Server className="w-5 h-5" />} title="ACE Step Music Engine">
          <div className="space-y-3">
            <StatusRow label="Status" value={status?.ace_step?.loaded ? 'Loaded' : 'Not loaded'} ok={status?.ace_step?.loaded} />
            <StatusRow label="API URL" value={status?.ace_step?.api_url || '—'} />
            <button
              onClick={handleLoadAce}
              disabled={loadingAce}
              className="flex items-center gap-2 px-4 py-2 rounded-xl bg-gem-500/15 text-gem-300 text-sm font-medium border border-gem-500/30 hover:bg-gem-500/25 disabled:opacity-50 transition-all"
            >
              {loadingAce ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Music className="w-3.5 h-3.5" />}
              {loadingAce ? 'Loading...' : 'Load ACE Step'}
            </button>
            {aceMsg && <p className="text-xs text-zinc-400">{aceMsg}</p>}
          </div>
        </Card>

        <Card icon={<Brain className="w-5 h-5" />} title="LM Studio (LLM)">
          <div className="space-y-2">
            <StatusRow label="Available" value={status?.lm_studio?.available ? 'Yes' : 'No'} ok={status?.lm_studio?.available} />
            {status?.lm_studio?.models && (status.lm_studio.models as unknown[]).length > 0 && (
              <div className="space-y-1">
                <span className="text-xs text-zinc-500">Loaded models:</span>
                {(status.lm_studio.models as unknown[]).map((m: unknown) => (
                  <div key={typeof m === 'string' ? m : (m as Record<string, unknown>).id as string} className="text-xs text-zinc-300 bg-surface rounded-lg px-3 py-1.5 font-mono truncate">
                    {typeof m === 'string' ? m : (m as Record<string, unknown>).id as string}
                  </div>
                ))}
              </div>
            )}
          </div>
        </Card>

        <Card icon={<Database className="w-5 h-5" />} title="Knowledge Base">
          <div className="space-y-2">
            <StatusRow label="Ready" value={status?.knowledge_base?.ready ? 'Yes' : 'No'} ok={status?.knowledge_base?.ready} />
            {status?.knowledge_base?.stats && (
              <div className="grid grid-cols-2 gap-2 text-xs">
                {Object.entries(status.knowledge_base.stats).map(([key, val]) => (
                  <div key={key} className="flex justify-between bg-surface rounded-lg px-3 py-1.5">
                    <span className="text-zinc-500">{key}</span>
                    <span className="text-gem-300 font-mono">{String(val)}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </Card>

        <button
          onClick={refresh}
          disabled={loading}
          className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-surface-card border border-border-subtle text-sm text-zinc-400 hover:text-zinc-200 hover:border-border-default transition-all"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh Status
        </button>
      </div>
    </div>
  )
}

function Card({ icon, title, children }: { icon: React.ReactNode; title: string; children: React.ReactNode }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl bg-surface-card border border-border-subtle p-5 space-y-3"
    >
      <h3 className="font-semibold text-zinc-200 flex items-center gap-2">{icon}{title}</h3>
      {children}
    </motion.div>
  )
}

function StatusRow({ label, value, ok }: { label: string; value: string; ok?: boolean }) {
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-zinc-400">{label}</span>
      <span className={ok ? 'text-emerald-400' : ok === false ? 'text-red-400' : 'text-zinc-300'}>{value}</span>
    </div>
  )
}
