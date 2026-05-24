import { useState, useEffect, useCallback, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Sparkles, Wand2, Loader2, Play, Pause, Music, Mic, ChevronDown, CheckCircle2, AlertCircle, Search, Users, X, RefreshCw, FileText, UserPlus, Star, Zap, PenLine } from 'lucide-react'
import {
  api, type GenerateResponse, type BackingVocals, type BackingVocalStyle,
  type LyricsLanguage, type OptimizePromptResponse, type ReferenceTrackWithSelection,
  type ArtistSearchResult, type ArtistStats, type VoiceType,
} from '../lib/api'
import { useApp } from '../context/AppContext'

type Step = 'input' | 'optimized' | 'lyrics' | 'ready'
type Mode = 'artist' | 'custom'

const GENRE_PRESETS = [
  'pop', 'hip hop', 'rock', 'r&b', 'dance/electronic', 'latin',
  'indie', 'k-pop', 'acoustic', 'metal', 'reggaeton', 'country',
  'folk', 'jazz',
]

const MOOD_CATEGORIES: Record<string, { label: string; moods: { label: string; id: string }[] }> = {
  'Energy': {
    label: 'Energy',
    moods: [
      { label: 'Euphoric', id: 'euphoric' }, { label: 'Energetic', id: 'energetic' },
      { label: 'Driving', id: 'driving' }, { label: 'Chill', id: 'chill' },
      { label: 'Dreamy', id: 'dreamy' }, { label: 'Melancholic', id: 'melancholic' },
    ],
  },
  'Vibe': {
    label: 'Vibe',
    moods: [
      { label: 'Dark', id: 'dark' }, { label: 'Mysterious', id: 'mysterious' },
      { label: 'Romantic', id: 'romantic' }, { label: 'Sensual', id: 'sensual' },
      { label: 'Nostalgic', id: 'nostalgic' }, { label: 'Uplifting', id: 'uplifting' },
    ],
  },
}

const VOICE_OPTIONS: { value: VoiceType; label: string; desc: string }[] = [
  { value: 'male', label: 'Male', desc: 'Male vocalist' },
  { value: 'female', label: 'Female', desc: 'Female vocalist' },
  { value: 'male_female', label: 'Male + Female', desc: 'Male lead, female backing' },
  { value: 'female_male', label: 'Female + Male', desc: 'Female lead, male backing' },
  { value: 'duet', label: 'Duet', desc: 'Equal male + female' },
  { value: 'instrumental', label: 'Instrumental', desc: 'No vocals' },
]

const BACKING_OPTIONS: { value: BackingVocals; label: string }[] = [
  { value: 'none', label: 'None' },
  { value: 'harmony', label: 'Harmony' },
  { value: 'call_response', label: 'Call & Response' },
  { value: 'choir', label: 'Choir' },
]

const BACKING_STYLE_OPTIONS: { value: BackingVocalStyle; label: string }[] = [
  { value: 'higher_third', label: '3rd Above' },
  { value: 'fifth_above', label: '5th Above' },
  { value: 'falsetto', label: 'Falsetto' },
  { value: 'same_octave', label: 'Same Octave' },
]

const PRIMARY_LANGUAGES: { value: LyricsLanguage; label: string; flag: string }[] = [
  { value: 'en', label: 'English', flag: 'EN' },
  { value: 'es', label: 'Espa\u00f1ol', flag: 'ES' },
  { value: 'pt', label: 'Portugu\u00eas', flag: 'PT' },
]

const DEFAULT_SONG_STRUCTURE = `[Intro]
[Verse 1]
[Pre-Chorus]
[Chorus]
[Verse 2]
[Pre-Chorus]
[Chorus]
[Bridge]
[Chorus]
[Outro]`

const KEY_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

function formatKey(key: number | null | undefined, mode: number | null | undefined): string {
  if (key == null) return 'C major'
  const keyName = KEY_NAMES[key % 12] || `Key ${key}`
  return `${keyName} ${mode === 1 ? 'major' : 'minor'}`
}

export function GeneratePage() {
  const { genres, status } = useApp()

  const [mode, setMode] = useState<Mode>('artist')
  const [step, setStep] = useState<Step>('input')

  const [language, setLanguage] = useState<LyricsLanguage>('es')

  const [artistQuery, setArtistQuery] = useState('')
  const [artistResults, setArtistResults] = useState<ArtistSearchResult[]>([])
  const [artistSearching, setArtistSearching] = useState(false)
  const [artistDropdownOpen, setArtistDropdownOpen] = useState(false)
  const [whichSlot, setWhichSlot] = useState<'primary' | 'secondary'>('primary')
  const artistSearchRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const artistInputRef = useRef<HTMLInputElement>(null)

  const [primaryArtist, setPrimaryArtist] = useState<string>('')
  const [primaryStats, setPrimaryStats] = useState<ArtistStats | null>(null)
  const [secondaryArtists, setSecondaryArtists] = useState<string[]>([])
  const [expandedArtists, setExpandedArtists] = useState<string[]>([])
  const [genreOverride, setGenreOverride] = useState<string>('')

  const [sessionId, setSessionId] = useState('')

  const [prompt, setPrompt] = useState('')
  const [genre, setGenre] = useState('')
  const [lyrics, setLyrics] = useState('')
  const [duration, setDuration] = useState(30)
  const [mood, setMood] = useState('')
  const [autoMood, setAutoMood] = useState('')
  const [useHitProfile, setUseHitProfile] = useState(true)
  const [showVoice, setShowVoice] = useState(false)
  const [voiceType, setVoiceType] = useState<VoiceType | null>(null)
  const [backingVocals, setBackingVocals] = useState<BackingVocals | null>(null)
  const [backingVocalStyle, setBackingVocalStyle] = useState<BackingVocalStyle | null>(null)

  const [optimizing, setOptimizing] = useState(false)
  const [composing, setComposing] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState('')

  const [optimized, setOptimized] = useState<OptimizePromptResponse | null>(null)
  const [refTracks, setRefTracks] = useState<ReferenceTrackWithSelection[]>([])
  const [selectedTrackIds, setSelectedTrackIds] = useState<Set<string>>(new Set())
  const [songStructure, setSongStructure] = useState(DEFAULT_SONG_STRUCTURE)

  const [autoParams, setAutoParams] = useState<{
    bpm?: number
    key_scale?: string
    derived_mood?: string
    dominant_genre?: string
    top_genres?: { genre: string; count: number }[]
    avg_duration_ms?: number
    dominant_key?: number
    dominant_mode?: number
  } | null>(null)

  const [result, setResult] = useState<GenerateResponse | null>(null)
  const [playing, setPlaying] = useState(false)
  const [audioReady, setAudioReady] = useState(false)
  const [audioUrl, setAudioUrl] = useState('')
  const [pollingId, setPollingId] = useState<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent).detail
      if (detail?.prompt) {
        setPrompt(detail.prompt)
        if (detail.genre) setGenre(detail.genre)
        resetPipeline()
      }
    }
    window.addEventListener('use-reference', handler)
    return () => window.removeEventListener('use-reference', handler)
  }, [])

  useEffect(() => {
    setPrimaryArtist('')
    setPrimaryStats(null)
    setSecondaryArtists([])
    setExpandedArtists([])
    setAutoParams(null)
    setGenreOverride('')
    resetPipeline()
  }, [language])

  const resetPipeline = useCallback(() => {
    setStep('input')
    setOptimized(null)
    setRefTracks([])
    setSelectedTrackIds(new Set())
    setLyrics('')
    setAutoMood('')
    setAutoParams(null)
    setExpandedArtists([])
    setSessionId('')
    setError('')
  }, [])

  const searchArtistsDebounced = useCallback((q: string, lang: string) => {
    if (artistSearchRef.current) clearTimeout(artistSearchRef.current)
    if (q.length < 2) { setArtistResults([]); setArtistDropdownOpen(false); return }
    setArtistSearching(true)
    artistSearchRef.current = setTimeout(async () => {
      try {
        const results = await api.searchArtists(q, lang)
        setArtistResults(results)
        setArtistDropdownOpen(results.length > 0)
      } catch { setArtistResults([]) }
      setArtistSearching(false)
    }, 300)
  }, [])

  const startArtistSearch = (slot: 'primary' | 'secondary') => {
    setWhichSlot(slot)
    setArtistQuery('')
    setArtistResults([])
    setArtistDropdownOpen(false)
    setTimeout(() => artistInputRef.current?.focus(), 50)
  }

  const handleArtistSelect = useCallback(async (artist: ArtistSearchResult) => {
    setArtistDropdownOpen(false)
    setArtistQuery('')
    if (whichSlot === 'primary' || !primaryArtist) {
      setPrimaryArtist(artist.name)
      try {
        const stats = await api.getArtistStats(artist.name, language)
        setPrimaryStats(stats)
        if (stats.top_genres?.length && !genreOverride) {
          setGenreOverride(stats.top_genres[0].genre)
        }
      } catch { setPrimaryStats(null) }
    } else if (secondaryArtists.length < 2 && artist.name !== primaryArtist && !secondaryArtists.includes(artist.name)) {
      setSecondaryArtists(prev => [...prev, artist.name])
    }
    resetPipeline()
  }, [whichSlot, primaryArtist, secondaryArtists, language, genreOverride, resetPipeline])

  const removeSecondary = (name: string) => {
    setSecondaryArtists(prev => prev.filter(a => a !== name))
    resetPipeline()
  }

  const removePrimary = () => {
    setPrimaryArtist('')
    setPrimaryStats(null)
    setSecondaryArtists([])
    setAutoParams(null)
    setGenreOverride('')
    resetPipeline()
  }

  const handleOptimizeArtist = async () => {
    if (!primaryArtist) return
    setOptimizing(true)
    setError('')
    try {
      const res = await api.optimizePromptArtist({
        primary_artist: primaryArtist,
        secondary_artists: secondaryArtists,
        language,
        voice_type: voiceType || undefined,
        custom_prompt: prompt.trim() || undefined,
        genre_override: genreOverride || undefined,
      })
    setOptimized(res)
    setSessionId(res.session_id)
    setPrompt(res.optimized_prompt)
    setAutoMood(res.mood)
    setRefTracks(res.reference_tracks)
    const preSelected = new Set(res.reference_tracks.filter(t => t.selected).map(t => t.track_id))
    setSelectedTrackIds(preSelected)
    if (res.song_structure) setSongStructure(res.song_structure)
    if (res.auto_params) setAutoParams(res.auto_params as typeof autoParams)
    if (res.expanded_artists) setExpandedArtists(res.expanded_artists)
    const selectedTracks = res.reference_tracks.filter(t => t.selected)
    if (selectedTracks.length > 0) {
      const avgDur = selectedTracks.reduce((sum, t) => sum + (t.duration_ms || 0), 0) / selectedTracks.length
      if (avgDur > 0) setDuration(Math.round(avgDur / 1000))
    }
    setStep('optimized')
  } catch (e) {
      setError(e instanceof Error ? e.message : 'Optimize failed')
    }
    setOptimizing(false)
  }

  const handleOptimizeCustom = async () => {
    if (!prompt.trim()) return
    setOptimizing(true)
    setError('')
    try {
      const res = await api.optimizePrompt({
        prompt: prompt.trim(),
        genre: genre || undefined,
        mood: mood || undefined,
        voice_type: (voiceType as 'male' | 'female' | 'duet' | 'instrumental') || undefined,
      })
    setOptimized(res)
    setSessionId(res.session_id)
    setPrompt(res.optimized_prompt)
    setAutoMood(res.mood)
    setRefTracks(res.reference_tracks)
      const preSelected = new Set(res.reference_tracks.filter(t => t.selected).map(t => t.track_id))
      setSelectedTrackIds(preSelected)
      if (res.song_structure) setSongStructure(res.song_structure)
      setStep('optimized')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Optimize failed')
    }
    setOptimizing(false)
  }

  const toggleRefTrack = (trackId: string) => {
    setSelectedTrackIds(prev => {
      const next = new Set(prev)
      if (next.has(trackId)) next.delete(trackId)
      else next.add(trackId)
      return next
    })
  }

  const handleComposeLyrics = async () => {
    if (!optimized || selectedTrackIds.size === 0) return
    setComposing(true)
    setError('')
    try {
      const res = await api.composeLyrics({
        session_id: sessionId,
        prompt: optimized.optimized_prompt,
        selected_track_ids: Array.from(selectedTrackIds),
        genre: genreOverride || genre || undefined,
        mood: mood || autoMood || undefined,
        voice_type: (voiceType as 'male' | 'female' | 'duet' | 'instrumental') || undefined,
        backing_vocals: backingVocals || undefined,
        lyrics_language: language || undefined,
      })
      setLyrics(res.lyrics)
      if (res.session_id) setSessionId(res.session_id)
      setStep('lyrics')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Lyrics composition failed')
    }
    setComposing(false)
  }

  const handleRerollLyrics = async () => {
    if (!optimized || selectedTrackIds.size === 0) return
    setComposing(true)
    setError('')
    try {
      const res = await api.composeLyrics({
        session_id: sessionId,
        prompt: optimized.optimized_prompt,
        selected_track_ids: Array.from(selectedTrackIds),
        genre: genreOverride || genre || undefined,
        mood: mood || autoMood || undefined,
        backing_vocals: backingVocals || undefined,
        lyrics_language: language || undefined,
      })
      setLyrics(res.lyrics)
      if (res.session_id) setSessionId(res.session_id)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Lyrics reroll failed')
    }
    setComposing(false)
  }

  const handleGenerate = async () => {
    if (!optimized) return
    if (pollingId) clearInterval(pollingId)
    setGenerating(true)
    setError('')
    setResult(null)
    setAudioReady(false)
    setAudioUrl('')
    setPollingId(null)
    try {
      const req = {
        session_id: sessionId,
        prompt: optimized.original_prompt,
        optimized_prompt: optimized.optimized_prompt,
        genre: genreOverride || genre || undefined,
        mood: mood || autoMood || undefined,
        lyrics: lyrics || undefined,
        use_hit_profile: useHitProfile,
        duration_seconds: duration,
        voice_type: voiceType || undefined,
        backing_vocals: backingVocals || undefined,
        backing_vocal_style: backingVocalStyle || undefined,
        lyrics_language: language || undefined,
        bpm: optimized.bpm,
        key_scale: optimized.key_scale,
        time_signature: optimized.time_signature,
        song_structure: songStructure || undefined,
      }
      const res = await api.generate(req)
      setResult(res)
      setStep('ready')
      setGenerating(false)
      const id = setInterval(async () => {
        try {
          const track = await api.getTrack(res.id)
          if (track.audio_path && track.audio_path !== 'pending') {
            const filename = track.audio_path.replace(/\\/g, '/').split('/').pop()
            setResult(prev => prev ? { ...prev, audio_path: track.audio_path, hit_prediction_score: track.hit_prediction_score, hit_prediction_label: track.hit_prediction_label, pipeline_trace: track.pipeline_trace } : prev)
            setAudioUrl(`/audio/${filename}`)
            setAudioReady(true)
            clearInterval(id)
            setPollingId(null)
          }
        } catch { clearInterval(id); setPollingId(null) }
      }, 5000)
      setPollingId(id)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Generation failed')
      setGenerating(false)
    }
  }

  const activeMoodObj = Object.values(MOOD_CATEGORIES).flatMap(c => c.moods).find(m => m.id === (mood || autoMood))

  const stepLabels: Record<Step, string> = {
    input: '1. Describe',
    optimized: '2. Refine',
    lyrics: '3. Lyrics',
    ready: '4. Generate',
  }

  const canCompose = step === 'optimized' && selectedTrackIds.size > 0
  const canGenerate = (step === 'lyrics' || step === 'ready') && optimized != null

  const primaryGenreOptions = primaryStats?.top_genres?.map(g => g.genre) || []

  return (
    <div className="space-y-6">
      <div className="text-center space-y-2">
        <motion.h1 initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="text-4xl sm:text-5xl font-bold tracking-tight gradient-text">
          Create Your Hit
        </motion.h1>
        <p className="text-zinc-500 text-sm max-w-md mx-auto">
          {mode === 'artist' ? 'Select artists \u2192 Auto-derive params \u2192 Compose \u2192 Generate' : 'Write prompt \u2192 Optimize \u2192 Compose \u2192 Generate'}
        </p>
      </div>

      {/* Step indicator */}
      <div className="flex items-center justify-center gap-1">
        {(Object.keys(stepLabels) as Step[]).map((s, i) => {
          const stepOrder = { input: 0, optimized: 1, lyrics: 2, ready: 3 }[s]
          const currentOrder = { input: 0, optimized: 1, lyrics: 2, ready: 3 }[step]
          const isActive = step === s
          const isDone = currentOrder > stepOrder
          return (
            <div key={s} className="flex items-center gap-1">
              {i > 0 && <div className={`w-6 h-px ${isDone ? 'bg-gem-500' : 'bg-border-subtle'}`} />}
              <div className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                isActive ? 'bg-gem-500/20 border border-gem-500/40 text-gem-300' :
                isDone ? 'bg-gem-500/5 border border-gem-500/20 text-gem-400' :
                'bg-surface border border-border-subtle text-zinc-600'
              }`}>
                {isDone ? <CheckCircle2 className="w-3 h-3 inline mr-1" /> : null}
                {stepLabels[s]}
              </div>
            </div>
          )
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">

        {/* LEFT: Controls (3 cols) */}
        <div className="lg:col-span-3 space-y-4">
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
            className="rounded-2xl bg-surface-card border border-border-subtle p-5 space-y-4">

            {/* Mode toggle + Language */}
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-1 p-1 bg-surface rounded-xl border border-border-subtle flex-1">
                <button onClick={() => { setMode('artist'); resetPipeline() }}
                  className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                    mode === 'artist' ? 'bg-gem-500/20 border border-gem-500/40 text-gem-300' : 'text-zinc-500 hover:text-zinc-300'
                  }`}>
                  <Star className="w-3.5 h-3.5" /> Artist
                </button>
                <button onClick={() => { setMode('custom'); resetPipeline() }}
                  className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                    mode === 'custom' ? 'bg-gem-500/20 border border-gem-500/40 text-gem-300' : 'text-zinc-500 hover:text-zinc-300'
                  }`}>
                  <Sparkles className="w-3.5 h-3.5" /> Custom
                </button>
              </div>
              <div className="flex gap-1">
                {PRIMARY_LANGUAGES.map(l => (
                  <button key={l.value} onClick={() => setLanguage(l.value)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all border ${
                      language === l.value
                        ? 'bg-gem-500/20 border-gem-500/40 text-gem-300'
                        : 'bg-surface border-border-subtle text-zinc-400 hover:border-border-default'
                    }`}>
                    {l.flag}
                  </button>
                ))}
              </div>
            </div>

            {mode === 'artist' && (
              <>
                {/* Selected artists */}
                <div className="space-y-2">
                  <label className="text-xs font-medium text-zinc-400 uppercase tracking-wider">Artists</label>
                  <div className="flex flex-wrap gap-1.5">
                    {primaryArtist ? (
                      <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium bg-emerald-500/15 border border-emerald-500/30 text-emerald-300">
                        <span className="text-[9px] font-bold bg-emerald-500/30 px-1 py-0.5 rounded">60%</span>
                        {primaryArtist}
                        <button onClick={removePrimary} className="ml-0.5 hover:text-red-400"><X className="w-3 h-3" /></button>
                      </span>
                    ) : (
                      <button onClick={() => startArtistSearch('primary')}
                        className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium bg-surface border border-dashed border-zinc-600 text-zinc-500 hover:border-gem-500/40 hover:text-gem-300 transition-all">
                        <UserPlus className="w-3 h-3" /> Add primary
                      </button>
                    )}
                    {primaryArtist && secondaryArtists.map((a, i) => (
                      <span key={a} className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium bg-amber-500/15 border border-amber-500/30 text-amber-300">
                        <span className="text-[9px] font-bold bg-amber-500/30 px-1 py-0.5 rounded">{i === 0 ? '30%' : '10%'}</span>
                        {a}
                        <button onClick={() => removeSecondary(a)} className="ml-0.5 hover:text-red-400"><X className="w-3 h-3" /></button>
                      </span>
                    ))}
                    {primaryArtist && secondaryArtists.length < 2 && (
                      <button onClick={() => startArtistSearch('secondary')}
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs bg-surface border border-dashed border-zinc-600 text-zinc-500 hover:border-gem-500/40 hover:text-gem-300 transition-all">
                        <UserPlus className="w-3 h-3" /> {secondaryArtists.length === 0 ? 'Add secondary' : '+1'}
                      </button>
                    )}
                    {expandedArtists.map(a => (
                      <span key={a} className="inline-flex items-center gap-1 px-2 py-1 rounded-lg text-[11px] font-medium bg-violet-500/10 border border-violet-500/20 text-violet-400">
                        <Zap className="w-2.5 h-2.5" />{a}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Artist search input */}
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-zinc-500" />
                  <input
                    ref={artistInputRef}
                    type="text"
                    value={artistQuery}
                    onChange={(e) => { setArtistQuery(e.target.value); searchArtistsDebounced(e.target.value, language) }}
                    onFocus={() => { if (artistResults.length > 0) setArtistDropdownOpen(true) }}
                    onBlur={() => setTimeout(() => setArtistDropdownOpen(false), 200)}
                    placeholder={whichSlot === 'primary' ? "Search primary artist..." : "Search secondary artist..."}
                    className="w-full pl-9 pr-4 py-2 rounded-xl bg-surface border border-border-subtle text-zinc-100 placeholder-zinc-600 focus:outline-none focus:ring-2 focus:ring-gem-500/50 focus:border-gem-500/50 text-sm transition-all"
                  />
                  {artistSearching && <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 animate-spin text-gem-400" />}
                  <AnimatePresence>
                    {artistDropdownOpen && artistResults.length > 0 && (
                      <motion.div initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -4 }}
                        className="absolute z-50 mt-1 w-full bg-surface-card border border-border-subtle rounded-xl shadow-xl overflow-hidden max-h-52 overflow-y-auto">
                        {artistResults.map((a) => (
                          <button key={a.name} onMouseDown={() => handleArtistSelect(a)}
                            className="w-full flex items-center justify-between px-3 py-2 hover:bg-gem-500/10 transition-colors text-left"
                            disabled={a.name === primaryArtist || secondaryArtists.includes(a.name)}>
                            <div>
                              <div className="text-sm text-zinc-200">{a.name}</div>
                              <div className="flex items-center gap-2 text-[11px] text-zinc-500 mt-0.5">
                                <span>{a.track_count} tracks</span>
                                <span>{a.lyrics_count} lyrics</span>
                                {a.top_genres?.slice(0, 3).map(tg => (
                                  <span key={tg.genre} className="text-zinc-400">{tg.genre} <span className="text-zinc-600">{tg.count}</span></span>
                                ))}
                              </div>
                            </div>
                            {(a.name === primaryArtist || secondaryArtists.includes(a.name)) && (
                              <CheckCircle2 className="w-3.5 h-3.5 text-gem-400 shrink-0" />
                            )}
                          </button>
                        ))}
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>

                {/* Artist stats + genre override */}
                {primaryStats && (
                  <div className="bg-surface rounded-xl border border-border-subtle p-3 space-y-2">
                    <div className="flex flex-wrap gap-1.5">
                      <span className="text-[11px] bg-gem-500/10 text-gem-300 px-2 py-0.5 rounded-md font-mono">{primaryStats.avg_bpm.toFixed(0)} BPM</span>
                      <span className="text-[11px] bg-gem-500/10 text-gem-300 px-2 py-0.5 rounded-md">{formatKey(primaryStats.dominant_key, primaryStats.dominant_mode)}</span>
                      <span className="text-[11px] bg-gem-500/10 text-gem-300 px-2 py-0.5 rounded-md">{primaryStats.derived_mood}</span>
                      <span className="text-[11px] bg-zinc-500/10 text-zinc-400 px-2 py-0.5 rounded-md">{primaryStats.track_count} tracks</span>
                      <span className="text-[11px] bg-zinc-500/10 text-zinc-400 px-2 py-0.5 rounded-md">{primaryStats.lyrics_count} lyrics</span>
                    </div>
                    {primaryGenreOptions.length > 1 && (
                      <div className="flex items-center gap-1.5 flex-wrap">
                        <span className="text-[10px] text-zinc-500 uppercase tracking-wider">Genre:</span>
                        {primaryStats.top_genres.map(tg => (
                          <button key={tg.genre} onClick={() => { setGenreOverride(genreOverride === tg.genre ? '' : tg.genre); resetPipeline() }}
                            className={`text-[11px] px-2 py-0.5 rounded-md font-medium transition-all border ${
                              genreOverride === tg.genre
                                ? 'bg-gem-500/20 border-gem-500/40 text-gem-300'
                                : 'bg-surface border-border-subtle text-zinc-400 hover:border-border-default'
                            }`}>
                            {tg.genre} <span className="text-zinc-600">{tg.count}</span>
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {/* Optional custom prompt */}
                <div className="space-y-1">
                  <label className="text-xs text-zinc-500 flex items-center gap-1.5">
                    <PenLine className="w-3 h-3" /> Extra direction <span className="text-zinc-600">(optional)</span>
                  </label>
                  <textarea
                    value={prompt} onChange={(e) => { setPrompt(e.target.value); if (step !== 'input') resetPipeline() }}
                    placeholder="e.g. 'perreo intenso con bajo 808' or 'dreamy lo-fi vibe'"
                    className="w-full h-16 px-3 py-2 rounded-xl bg-surface border border-border-subtle text-zinc-100 placeholder-zinc-600 focus:outline-none focus:ring-2 focus:ring-gem-500/50 resize-none text-sm transition-all"
                  />
                </div>
              </>
            )}

            {mode === 'custom' && (
              <>
                <div className="space-y-1">
                  <label className="text-xs font-medium text-zinc-400 uppercase tracking-wider flex items-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5" /> Prompt
                  </label>
                  <textarea
                    value={prompt} onChange={(e) => { setPrompt(e.target.value); if (step !== 'input') resetPipeline() }}
                    placeholder="e.g. estilo Bad Bunny, perreo intenso con bajo 808..."
                    className="w-full h-24 px-3 py-2 rounded-xl bg-surface border border-border-subtle text-zinc-100 placeholder-zinc-600 focus:outline-none focus:ring-2 focus:ring-gem-500/50 resize-none text-sm transition-all"
                  />
                </div>
                <div className="space-y-2">
                  {Object.entries(MOOD_CATEGORIES).map(([catKey, cat]) => (
                    <div key={catKey}>
                      <span className="text-[10px] text-zinc-500 uppercase tracking-wider mb-0.5 block">{cat.label}</span>
                      <div className="flex flex-wrap gap-1">
                        {cat.moods.map((m) => (
                          <button key={m.id} onClick={() => setMood(mood === m.id ? '' : m.id)}
                            className={`px-2 py-0.5 rounded-md text-[11px] font-medium transition-all border ${
                              (mood || autoMood) === m.id
                                ? 'bg-gem-500/20 border-gem-500/40 text-gem-300'
                                : 'bg-surface border-border-subtle text-zinc-400 hover:border-border-default'
                            }`}>
                            {m.label}
                          </button>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <label className="text-xs text-zinc-500">Genre</label>
                    <select value={genre} onChange={(e) => { setGenre(e.target.value); if (step !== 'input') resetPipeline() }}
                      className="w-full px-3 py-2 rounded-xl bg-surface border border-border-subtle text-zinc-100 text-sm focus:outline-none focus:ring-2 focus:ring-gem-500/50 appearance-none cursor-pointer">
                      <option value="">Auto-detect</option>
                      {(genres.length ? genres : GENRE_PRESETS).map((g) => (
                        <option key={g} value={g}>{g}</option>
                      ))}
                    </select>
                  </div>
                  <div className="space-y-1">
                    <label className="text-xs text-zinc-500">Duration</label>
                    <div className="flex items-center gap-2">
                      <input type="range" min={15} max={120} step={5} value={duration}
                        onChange={(e) => setDuration(Number(e.target.value))} className="flex-1 accent-gem-500" />
                      <span className="text-xs text-gem-300 font-mono w-10 text-right">{duration}s</span>
                    </div>
                  </div>
                </div>
              </>
            )}

            {/* Voice section */}
            <div>
              <button onClick={() => setShowVoice(!showVoice)}
                className="flex items-center gap-1.5 text-xs text-zinc-400 hover:text-zinc-200 transition-colors">
                <Users className="w-3.5 h-3.5" /><span>Voice</span>
                <ChevronDown className={`w-3 h-3 transition-transform ${showVoice ? 'rotate-180' : ''}`} />
                {voiceType && <span className="text-gem-400 ml-1">{VOICE_OPTIONS.find(v => v.value === voiceType)?.label}</span>}
              </button>
              <AnimatePresence>
                {showVoice && (
                  <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.15 }} className="overflow-hidden">
                    <div className="mt-2 space-y-3">
                      <div className="flex flex-wrap gap-1.5">
                        {VOICE_OPTIONS.map((v) => (
                          <button key={v.value} onClick={() => setVoiceType(voiceType === v.value ? null : v.value)}
                            className={`px-2.5 py-1.5 rounded-lg text-[11px] font-medium transition-all border ${
                              voiceType === v.value ? 'bg-gem-500/20 border-gem-500/40 text-gem-300' : 'bg-surface border-border-subtle text-zinc-400 hover:border-border-default'
                            }`} title={v.desc}>
                            {v.label}
                          </button>
                        ))}
                      </div>
                      {voiceType && voiceType !== 'instrumental' && (
                        <>
                          <div className="flex flex-wrap gap-1.5">
                            {BACKING_OPTIONS.map((b) => (
                              <button key={b.value} onClick={() => setBackingVocals(backingVocals === b.value ? null : b.value)}
                                className={`px-2 py-1 rounded-md text-[11px] font-medium transition-all border ${
                                  backingVocals === b.value ? 'bg-gem-500/20 border-gem-500/40 text-gem-300' : 'bg-surface border-border-subtle text-zinc-400 hover:border-border-default'
                                }`}>
                                {b.label}
                              </button>
                            ))}
                          </div>
                          {backingVocals && backingVocals !== 'none' && (
                            <div className="flex flex-wrap gap-1.5">
                              {BACKING_STYLE_OPTIONS.map((s) => (
                                <button key={s.value} onClick={() => setBackingVocalStyle(backingVocalStyle === s.value ? null : s.value)}
                                  className={`px-2 py-1 rounded-md text-[11px] font-medium transition-all border ${
                                    backingVocalStyle === s.value ? 'bg-gem-500/20 border-gem-500/40 text-gem-300' : 'bg-surface border-border-subtle text-zinc-400 hover:border-border-default'
                                  }`}>
                                  {s.label}
                                </button>
                              ))}
                            </div>
                          )}
                        </>
                      )}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            {/* Duration (artist mode) */}
            {mode === 'artist' && (
              <div className="flex items-center gap-3">
                <label className="text-xs text-zinc-500 shrink-0">Duration</label>
                <input type="range" min={15} max={120} step={5} value={duration}
                  onChange={(e) => setDuration(Number(e.target.value))} className="flex-1 accent-gem-500" />
                <span className="text-xs text-gem-300 font-mono w-10 text-right">{duration}s</span>
                {autoParams?.avg_duration_ms && (
                  <span className="text-[10px] text-zinc-600">avg {(autoParams.avg_duration_ms / 1000).toFixed(0)}s</span>
                )}
              </div>
            )}

            {/* Action buttons */}
            <div className="flex items-center justify-between pt-1">
              <label className="flex items-center gap-1.5 cursor-pointer">
                <input type="checkbox" checked={useHitProfile} onChange={(e) => setUseHitProfile(e.target.checked)}
                  className="w-3.5 h-3.5 rounded border-border-subtle bg-surface text-gem-500 focus:ring-gem-500/50 accent-gem-500" />
                <span className="text-xs text-zinc-500">Hit profile</span>
              </label>
              <div className="flex gap-2">
                {step === 'input' && mode === 'artist' && (
                  <button onClick={handleOptimizeArtist} disabled={optimizing || !primaryArtist}
                    className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-gem-600 to-gem-500 text-white font-semibold text-sm shadow-lg shadow-gem-500/25 hover:shadow-gem-500/40 disabled:opacity-50 disabled:cursor-not-allowed transition-all">
                    {optimizing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />} Optimize
                  </button>
                )}
                {step === 'input' && mode === 'custom' && (
                  <button onClick={handleOptimizeCustom} disabled={optimizing || !prompt.trim()}
                    className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-gem-600 to-gem-500 text-white font-semibold text-sm shadow-lg shadow-gem-500/25 hover:shadow-gem-500/40 disabled:opacity-50 disabled:cursor-not-allowed transition-all">
                    {optimizing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />} Optimize
                  </button>
                )}
                {step === 'optimized' && (
                  <button onClick={handleComposeLyrics} disabled={composing || selectedTrackIds.size === 0}
                    className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-gem-600 to-gem-500 text-white font-semibold text-sm shadow-lg shadow-gem-500/25 hover:shadow-gem-500/40 disabled:opacity-50 disabled:cursor-not-allowed transition-all">
                    {composing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Mic className="w-4 h-4" />} Compose Lyrics
                  </button>
                )}
                {canGenerate && (
                  <button onClick={handleGenerate} disabled={generating}
                    className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-gem-600 to-gem-500 text-white font-semibold text-sm shadow-lg shadow-gem-500/25 hover:shadow-gem-500/40 disabled:opacity-50 disabled:cursor-not-allowed transition-all">
                    {generating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Wand2 className="w-4 h-4" />} Generate
                  </button>
                )}
              </div>
            </div>
          </motion.div>

          {/* Reference tracks */}
          <AnimatePresence>
            {optimized && refTracks.length > 0 && (
              <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }}
                className="rounded-2xl bg-surface-card border border-border-subtle p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Reference Tracks</h3>
                  <span className="text-[11px] text-zinc-500">{selectedTrackIds.size} selected</span>
                </div>
                <div className="space-y-1.5 max-h-56 overflow-y-auto">
                  {refTracks.map((t) => (
                    <label key={t.track_id}
                      className={`flex items-center gap-2.5 px-2.5 py-1.5 rounded-lg cursor-pointer transition-all ${
                        selectedTrackIds.has(t.track_id) ? 'bg-gem-500/10 border border-gem-500/20' : 'bg-surface border border-border-subtle hover:border-border-default'
                      }`}>
                      <input type="checkbox" checked={selectedTrackIds.has(t.track_id)}
                        onChange={() => toggleRefTrack(t.track_id)}
                        className="w-3 h-3 rounded accent-gem-500 shrink-0" />
                      <div className="min-w-0 flex-1">
                        <div className="text-xs text-zinc-300 truncate">{t.track_name} <span className="text-zinc-600">\u2014 {t.artist_name}</span></div>
                        <div className="flex gap-1.5 text-[10px] text-zinc-500 mt-0.5">
                          {t.track_genre && <span>{t.track_genre}</span>}
                          <span>{t.tempo.toFixed(0)}bpm</span>
                          {t.ref_role && (
                            <span className={`px-1 py-0 rounded text-[9px] font-bold uppercase ${
                              t.ref_role === 'primary' ? 'text-emerald-400' :
                              t.ref_role === 'contrast' ? 'text-amber-400' :
                              'text-violet-400'
                            }`}>
                              {t.ref_role === 'primary' ? '60' : t.ref_role === 'contrast' ? '30' : '10'}%
                            </span>
                          )}
                        </div>
                      </div>
                    </label>
                  ))}
                </div>
                {canCompose && (
                  <button onClick={handleComposeLyrics} disabled={composing || selectedTrackIds.size === 0}
                    className="w-full flex items-center justify-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r from-gem-600 to-gem-500 text-white font-semibold text-sm shadow-lg shadow-gem-500/25 disabled:opacity-50 disabled:cursor-not-allowed transition-all">
                    {composing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Mic className="w-3.5 h-3.5" />}
                    Compose Lyrics
                  </button>
                )}
              </motion.div>
            )}
          </AnimatePresence>

          {/* Auto-params panel */}
          <AnimatePresence>
            {mode === 'artist' && (autoParams || (optimized && step !== 'input')) && (
              <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }}
                className="rounded-2xl bg-surface-card border border-gem-500/20 p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-semibold text-zem-400 uppercase tracking-wider text-zinc-400">Auto Parameters</h3>
                  <span className="text-[10px] text-gem-400">from {primaryArtist}</span>
                </div>
                <div className="flex gap-1.5 flex-wrap">
                  {optimized && <span className="text-[11px] bg-gem-500/10 text-gem-300 px-2 py-0.5 rounded-md font-mono">{optimized.bpm} BPM</span>}
                  {optimized && <span className="text-[11px] bg-gem-500/10 text-gem-300 px-2 py-0.5 rounded-md">{optimized.key_scale}</span>}
                  {(autoMood || autoParams?.derived_mood) && <span className="text-[11px] bg-gem-500/10 text-gem-300 px-2 py-0.5 rounded-md">{autoMood || autoParams?.derived_mood}</span>}
                  {(genreOverride || autoParams?.dominant_genre) && <span className="text-[11px] bg-gem-500/10 text-gem-300 px-2 py-0.5 rounded-md">{genreOverride || autoParams?.dominant_genre}</span>}
                  {voiceType && <span className="text-[11px] bg-gem-500/10 text-gem-300 px-2 py-0.5 rounded-md">{VOICE_OPTIONS.find(v => v.value === voiceType)?.label}</span>}
                  {language && <span className="text-[11px] bg-gem-500/10 text-gem-300 px-2 py-0.5 rounded-md">{PRIMARY_LANGUAGES.find(l => l.value === language)?.flag}</span>}
                </div>
                <div>
                  <h4 className="text-[10px] font-semibold text-zinc-500 uppercase tracking-wider mb-0.5">Song Structure</h4>
                  <textarea value={songStructure} onChange={(e) => setSongStructure(e.target.value)}
                    className="w-full h-20 px-2 py-1.5 rounded-lg bg-surface border border-border-subtle text-zinc-100 placeholder-zinc-600 focus:outline-none focus:ring-2 focus:ring-gem-500/50 resize-none text-[11px] transition-all font-mono" />
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Custom mode params panel */}
          <AnimatePresence>
            {mode === 'custom' && optimized && (
              <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }}
                className="rounded-2xl bg-surface-card border border-gem-500/20 p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Pipeline Parameters</h3>
                  <span className="text-[10px] text-gem-400">Optimized</span>
                </div>
                <div className="flex gap-1.5 flex-wrap">
                  <span className="text-[11px] bg-gem-500/10 text-gem-300 px-2 py-0.5 rounded-md font-mono">{optimized.bpm} BPM</span>
                  <span className="text-[11px] bg-gem-500/10 text-gem-300 px-2 py-0.5 rounded-md">{optimized.key_scale}</span>
                  <span className="text-[11px] bg-gem-500/10 text-gem-300 px-2 py-0.5 rounded-md">{optimized.time_signature}</span>
                </div>
                <div>
                  <h4 className="text-[10px] font-semibold text-zinc-500 uppercase tracking-wider mb-0.5">Song Structure</h4>
                  <textarea value={songStructure} onChange={(e) => setSongStructure(e.target.value)}
                    className="w-full h-20 px-2 py-1.5 rounded-lg bg-surface border border-border-subtle text-zinc-100 placeholder-zinc-600 focus:outline-none focus:ring-2 focus:ring-gem-500/50 resize-none text-[11px] transition-all font-mono" />
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          <AnimatePresence>
            {error && (
              <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }}
                className="rounded-xl bg-red-500/10 border border-red-500/30 px-4 py-2.5 text-sm text-red-300 flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" /> {error}
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* RIGHT: Lyrics + Result (2 cols) */}
        <div className="lg:col-span-2 space-y-4">

          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
            className="rounded-2xl bg-surface-card border border-border-subtle p-5 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider flex items-center gap-1.5">
                <FileText className="w-3.5 h-3.5 text-gem-400" /> Lyrics
                {language && <span className="text-gem-400 ml-1">{PRIMARY_LANGUAGES.find(l => l.value === language)?.flag}</span>}
              </h3>
              <div className="flex items-center gap-1.5">
                {(step === 'lyrics' || step === 'ready') && (
                  <button onClick={handleRerollLyrics} disabled={composing}
                    className="flex items-center gap-1 px-2 py-1 rounded-md bg-surface border border-border-subtle text-zinc-400 hover:text-gem-300 hover:border-gem-500/30 disabled:opacity-40 transition-all text-[11px]">
                    {composing ? <Loader2 className="w-3 h-3 animate-spin" /> : <RefreshCw className="w-3 h-3" />} Reroll
                  </button>
                )}
                {lyrics && (
                  <button onClick={() => setLyrics('')} className="flex items-center gap-1 text-[11px] text-zinc-500 hover:text-red-400 transition-colors">
                    <X className="w-3 h-3" /> Clear
                  </button>
                )}
              </div>
            </div>
            <textarea
              value={lyrics} onChange={(e) => setLyrics(e.target.value)}
              placeholder={step === 'input' ? 'Lyrics appear here after Optimize \u2192 Compose...' :
                step === 'optimized' ? 'Click "Compose Lyrics" to generate from selected references...' :
                'Edit lyrics or hit Reroll to regenerate...'}
              className="w-full h-56 px-3 py-2.5 rounded-xl bg-surface border border-border-subtle text-zinc-100 placeholder-zinc-600 focus:outline-none focus:ring-2 focus:ring-gem-500/50 resize-none text-sm transition-all font-mono"
            />
          </motion.div>

          {/* Result */}
          <AnimatePresence>
            {result && (
              <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }}
                className="rounded-2xl bg-surface-card border border-border-subtle p-5 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`w-10 h-10 rounded-xl flex items-center justify-center animate-float ${
                      audioReady ? 'bg-emerald-500/20 border border-emerald-500/30 text-emerald-400' : 'bg-gem-500/20 border border-gem-500/30 text-gem-400'
                    }`}>
                      {audioReady ? <CheckCircle2 className="w-5 h-5" /> : <Music className="w-5 h-5" />}
                    </div>
                    <div>
                      <h3 className="font-semibold text-zinc-100 text-sm">Track #{result.id}</h3>
                      <p className="text-[11px] text-zinc-500">{genreOverride || genre || 'Auto'} \u00b7 {duration}s
                        {voiceType && ` \u00b7 ${VOICE_OPTIONS.find(v => v.value === voiceType)?.label}`}
                        {activeMoodObj && ` \u00b7 ${activeMoodObj.label}`}
                      </p>
                    </div>
                  </div>
                  {result.hit_prediction_score > 0 && (
                    <div className="text-right">
                      <div className={`text-xl font-bold ${getHitColor(result.hit_prediction_score)}`}>
                        {(result.hit_prediction_score * 100).toFixed(0)}%
                      </div>
                      <div className="text-[10px] text-zinc-500">{result.hit_prediction_label || 'Hit Score'}</div>
                    </div>
                  )}
                </div>

                {!audioReady && (
                  <div className="flex items-center gap-2 text-xs text-gem-300 bg-gem-500/10 rounded-lg px-3 py-2">
                    <Loader2 className="w-3.5 h-3.5 animate-spin shrink-0" />
                    <span>Generating audio... ~4 min</span>
                  </div>
                )}

                {audioReady && (
                  <div className="space-y-2">
                    <audio src={audioUrl} onPlay={() => setPlaying(true)} onPause={() => setPlaying(false)}
                      onEnded={() => setPlaying(false)} className="hidden" id="audio-player" controls />
                    <button
                      onClick={() => {
                        const el = document.getElementById('audio-player') as HTMLAudioElement
                        if (playing) el?.pause(); else el?.play()
                      }}
                      className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-gem-500 text-white text-xs font-medium hover:bg-gem-400 transition-colors">
                      {playing ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
                      {playing ? 'Pause' : 'Play'}
                    </button>
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>

          {/* Status */}
          <div className="rounded-2xl bg-surface-card border border-border-subtle p-4 space-y-2">
            <h3 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider flex items-center gap-1.5">
              <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 shadow-sm shadow-emerald-400/50" /> Services
            </h3>
            <ServiceCard name="ACE Step" available={status?.ace_step?.loaded ?? false} />
            <ServiceCard name="LM Studio" available={status?.lm_studio?.available ?? false} />
            <ServiceCard name="Knowledge Base" available={status?.knowledge_base?.ready ?? false} />
          </div>
        </div>
      </div>
    </div>
  )
}

function ServiceCard({ name, available }: { name: string; available: boolean }) {
  return (
    <div className={`flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs ${
      available ? 'bg-emerald-500/5 border border-emerald-500/20' : 'bg-surface border border-border-subtle'
    }`}>
      <span className={available ? 'text-emerald-300' : 'text-zinc-500'}>{name}</span>
      <span className={`text-[10px] font-medium ${available ? 'text-emerald-400' : 'text-zinc-600'}`}>
        {available ? 'Online' : 'Offline'}
      </span>
    </div>
  )
}

function getHitColor(score: number): string {
  if (score >= 0.7) return 'text-emerald-400'
  if (score >= 0.4) return 'text-amber-400'
  return 'text-red-400'
}
