import { useState } from 'react'
import { motion } from 'framer-motion'
import { BarChart3, Zap, Loader2, TrendingUp, AlertCircle } from 'lucide-react'
import { api, type HitPredictionResponse } from '../lib/api'
import { useApp } from '../context/AppContext'

export function PredictPage() {
  const { genres } = useApp()
  const [features, setFeatures] = useState({
    danceability: 0.65,
    energy: 0.7,
    valence: 0.5,
    tempo: 120,
    loudness: -6,
    speechiness: 0.05,
    acousticness: 0.1,
    instrumentalness: 0.0,
    liveness: 0.1,
  })
  const [genre, setGenre] = useState('')
  const [result, setResult] = useState<HitPredictionResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handlePredict = async () => {
    setLoading(true)
    setError('')
    try {
      const res = await api.predictHit({ ...features, genre: genre || undefined })
      setResult(res)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Prediction failed')
    } finally {
      setLoading(false)
    }
  }

  const sliders: { key: keyof typeof features; label: string; min: number; max: number; step: number }[] = [
    { key: 'danceability', label: 'Danceability', min: 0, max: 1, step: 0.01 },
    { key: 'energy', label: 'Energy', min: 0, max: 1, step: 0.01 },
    { key: 'valence', label: 'Valence (Mood)', min: 0, max: 1, step: 0.01 },
    { key: 'speechiness', label: 'Speechiness', min: 0, max: 1, step: 0.01 },
    { key: 'acousticness', label: 'Acousticness', min: 0, max: 1, step: 0.01 },
    { key: 'instrumentalness', label: 'Instrumentalness', min: 0, max: 1, step: 0.01 },
    { key: 'liveness', label: 'Liveness', min: 0, max: 1, step: 0.01 },
  ]

  return (
    <div className="space-y-8">
      <div className="text-center space-y-2">
        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-4xl font-bold tracking-tight gradient-text"
        >
          Hit Predictor
        </motion.h1>
        <p className="text-zinc-400">Analyze audio features to predict hit potential</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="rounded-2xl bg-surface-card border border-border-subtle p-6 space-y-5"
        >
          <div className="space-y-4">
            {sliders.map(({ key, label, min, max, step }) => (
              <div key={key} className="space-y-1.5">
                <div className="flex justify-between text-sm">
                  <span className="text-zinc-400">{label}</span>
                  <span className="text-gem-300 font-mono">
                    {typeof features[key] === 'number' && features[key] < 1
                      ? (features[key] as number).toFixed(2)
                      : features[key]}
                  </span>
                </div>
                <input
                  type="range"
                  min={min}
                  max={max}
                  step={step}
                  value={features[key] as number}
                  onChange={(e) => setFeatures({ ...features, [key]: parseFloat(e.target.value) })}
                  className="w-full accent-gem-500"
                />
              </div>
            ))}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-sm text-zinc-400">Tempo (BPM)</label>
              <input
                type="number"
                value={features.tempo}
                onChange={(e) => setFeatures({ ...features, tempo: Number(e.target.value) })}
                min={0}
                max={300}
                className="w-full px-3 py-2 rounded-xl bg-surface border border-border-subtle text-sm text-zinc-100 focus:outline-none focus:ring-2 focus:ring-gem-500/50"
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-sm text-zinc-400">Loudness (dB)</label>
              <input
                type="number"
                value={features.loudness}
                onChange={(e) => setFeatures({ ...features, loudness: Number(e.target.value) })}
                min={-60}
                max={5}
                className="w-full px-3 py-2 rounded-xl bg-surface border border-border-subtle text-sm text-zinc-100 focus:outline-none focus:ring-2 focus:ring-gem-500/50"
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="text-sm text-zinc-400">Genre</label>
            <select
              value={genre}
              onChange={(e) => setGenre(e.target.value)}
              className="w-full px-3 py-2 rounded-xl bg-surface border border-border-subtle text-sm text-zinc-100 focus:outline-none focus:ring-2 focus:ring-gem-500/50 appearance-none cursor-pointer"
            >
              <option value="">Any genre</option>
              {genres.map((g) => <option key={g} value={g}>{g}</option>)}
            </select>
          </div>

          <button
            onClick={handlePredict}
            disabled={loading}
            className="w-full flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-gradient-to-r from-gem-600 to-gem-500 text-white font-semibold text-sm shadow-lg shadow-gem-500/25 hover:shadow-gem-500/40 disabled:opacity-50 transition-all"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <BarChart3 className="w-4 h-4" />}
            {loading ? 'Analyzing...' : 'Predict Hit Potential'}
          </button>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="space-y-6"
        >
          {error && (
            <div className="rounded-xl bg-red-500/10 border border-red-500/30 px-4 py-3 text-sm text-red-300 flex items-center gap-2">
              <AlertCircle className="w-4 h-4" /> {error}
            </div>
          )}

          {result ? (
            <div className="rounded-2xl bg-surface-card border border-border-subtle p-6 space-y-6">
              <div className="text-center space-y-2">
                <div className={`text-6xl font-bold ${getHitColor(result.hit_score)}`}>
                  {(result.hit_score * 100).toFixed(0)}%
                </div>
                <div className="text-lg font-medium text-zinc-300 flex items-center justify-center gap-2">
                  <TrendingUp className="w-5 h-5" />
                  {result.hit_label}
                </div>
                <div className="text-xs text-zinc-500">Confidence: {(result.confidence * 100).toFixed(0)}%</div>
              </div>

              <div className="h-4 rounded-full bg-surface overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${result.hit_score * 100}%` }}
                  transition={{ duration: 1, ease: 'easeOut' }}
                  className={`h-full rounded-full ${
                    result.hit_score >= 0.7
                      ? 'bg-gradient-to-r from-emerald-600 to-emerald-400'
                      : result.hit_score >= 0.4
                      ? 'bg-gradient-to-r from-amber-600 to-amber-400'
                      : 'bg-gradient-to-r from-red-600 to-red-400'
                  }`}
                />
              </div>

              {result.recommendations.length > 0 && (
                <div className="space-y-2">
                  <h4 className="text-sm font-medium text-zinc-300">Recommendations</h4>
                  <ul className="space-y-1.5">
                    {result.recommendations.map((rec, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-zinc-400">
                        <Zap className="w-3.5 h-3.5 text-gem-400 mt-0.5 shrink-0" />
                        {rec}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {result.ai_analysis && (
                <div className="space-y-2">
                  <h4 className="text-sm font-medium text-zinc-300">AI Analysis</h4>
                  <p className="text-sm text-zinc-400 leading-relaxed bg-surface rounded-xl p-3">
                    {result.ai_analysis}
                  </p>
                </div>
              )}
            </div>
          ) : (
            <div className="rounded-2xl bg-surface-card border border-border-subtle p-12 text-center text-zinc-500 space-y-3">
              <BarChart3 className="w-16 h-16 mx-auto text-zinc-700" />
              <p>Adjust audio features and click predict<br/>to see hit potential analysis</p>
            </div>
          )}
        </motion.div>
      </div>
    </div>
  )
}

function getHitColor(score: number): string {
  if (score >= 0.7) return 'text-emerald-400'
  if (score >= 0.4) return 'text-amber-400'
  return 'text-red-400'
}
