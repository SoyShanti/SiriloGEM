import { useState, useCallback, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Search, Music2, Users, FileText, Play, ChevronRight, Zap, Globe } from 'lucide-react'
import { api, type FullSearchResponse, type TrackSchema, type ArtistResultSchema, type LyricsResultSchema } from '../lib/api'

type SearchTab = 'all' | 'tracks' | 'artists' | 'lyrics'

export function DiscoverPage() {
  const [query, setQuery] = useState('')
  const [activeTab, setActiveTab] = useState<SearchTab>('all')
  const [results, setResults] = useState<FullSearchResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [expandedLyrics, setExpandedLyrics] = useState<Set<string>>(new Set())
  const inputRef = useRef<HTMLInputElement>(null)

  const doSearch = useCallback(async (q?: string, tab?: SearchTab) => {
    const searchQuery = q ?? query
    const searchType = tab ?? activeTab
    if (!searchQuery.trim()) return
    setLoading(true)
    try {
      const res = await api.fullSearch({
        query: searchQuery.trim(),
        search_type: searchType === 'all' ? 'all' : searchType === 'lyrics' ? 'lyrics' : searchType === 'artists' ? 'artist' : 'track',
        limit: 30,
      })
      setResults(res)
    } catch {
      setResults(null)
    } finally {
      setLoading(false)
    }
  }, [query, activeTab])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') doSearch()
  }

  const toggleLyrics = (trackId: string) => {
    setExpandedLyrics(prev => {
      const next = new Set(prev)
      if (next.has(trackId)) next.delete(trackId)
      else next.add(trackId)
      return next
    })
  }

  const useAsReference = (track: TrackSchema) => {
    const refPrompt = `estilo ${track.artist_name} ${track.track_name}`
    window.dispatchEvent(new CustomEvent('use-reference', { detail: { prompt: refPrompt, genre: track.track_genre } }))
  }

  const useLyricsAsReference = (lyric: LyricsResultSchema) => {
    const refPrompt = `estilo ${lyric.artist} ${lyric.track}`
    window.dispatchEvent(new CustomEvent('use-reference', { detail: { prompt: refPrompt } }))
  }

  const useArtistAsReference = (artist: ArtistResultSchema) => {
    const refPrompt = `estilo ${artist.name}`
    window.dispatchEvent(new CustomEvent('use-reference', { detail: { prompt: refPrompt } }))
  }

  const tabs: { id: SearchTab; label: string; icon: React.ReactNode; count: number }[] = [
    { id: 'all', label: 'All', icon: <Search className="w-4 h-4" />, count: results?.total ?? 0 },
    { id: 'tracks', label: 'Tracks', icon: <Music2 className="w-4 h-4" />, count: results?.tracks.length ?? 0 },
    { id: 'artists', label: 'Artists', icon: <Users className="w-4 h-4" />, count: results?.artists.length ?? 0 },
    { id: 'lyrics', label: 'Lyrics', icon: <FileText className="w-4 h-4" />, count: results?.lyrics.length ?? 0 },
  ]

  const showTracks = activeTab === 'all' || activeTab === 'tracks'
  const showArtists = activeTab === 'all' || activeTab === 'artists'
  const showLyrics = activeTab === 'all' || activeTab === 'lyrics'

  return (
    <div className="space-y-6">
      <div className="text-center space-y-2">
        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-4xl font-bold tracking-tight gradient-text"
        >
          Discover
        </motion.h1>
        <p className="text-zinc-400">Search 91K+ tracks, 57K lyrics by artist, track, genre, or lyrics text</p>
      </div>

      <div className="max-w-2xl mx-auto space-y-4">
        <div className="relative">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-zinc-500" />
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Search artist, track, genre, or lyrics... (e.g. Bad Bunny, perreo, pop)"
            className="w-full pl-12 pr-4 py-3.5 rounded-2xl bg-surface-card border border-border-subtle text-zinc-100 placeholder-zinc-600 focus:outline-none focus:ring-2 focus:ring-gem-500/50 focus:border-gem-500/50 text-sm transition-all"
          />
        </div>

        <div className="flex gap-2 p-1 bg-surface-card rounded-xl border border-border-subtle w-fit mx-auto">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => { setActiveTab(tab.id); if (query.trim()) doSearch(query, tab.id) }}
              className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                activeTab === tab.id ? 'bg-gem-500/15 text-gem-300' : 'text-zinc-400 hover:text-zinc-300'
              }`}
            >
              {tab.icon}
              {tab.label}
              {tab.count > 0 && <span className="text-xs opacity-60">({tab.count})</span>}
            </button>
          ))}
        </div>
      </div>

      {loading && (
        <div className="flex justify-center py-8">
          <div className="w-6 h-6 border-2 border-gem-500 border-t-transparent rounded-full animate-spin" />
        </div>
      )}

      {!loading && results && (
        <div className="space-y-6">
          <AnimatePresence mode="wait">
            {showArtists && results.artists.length > 0 && (
              <motion.div key="artists" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-3">
                <h2 className="text-sm font-semibold text-zinc-500 uppercase tracking-wider flex items-center gap-2">
                  <Users className="w-4 h-4" /> Artists
                </h2>
                <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                  {results.artists.map((artist, i) => (
                    <motion.div
                      key={artist.name}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: i * 0.03 }}
                      className="flex items-center justify-between px-4 py-3 rounded-xl bg-surface-card border border-border-subtle hover:border-gem-500/30 transition-all group cursor-pointer"
                      onClick={() => useArtistAsReference(artist)}
                    >
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-zinc-200 truncate">{artist.name}</p>
                        <p className="text-xs text-zinc-500">{artist.track_count} tracks · Avg pop {artist.avg_popularity.toFixed(0)}</p>
                      </div>
                      <div className="flex items-center gap-1 text-xs text-gem-400 opacity-0 group-hover:opacity-100 transition-opacity">
                        <Play className="w-3 h-3" /> Use
                      </div>
                    </motion.div>
                  ))}
                </div>
              </motion.div>
            )}

            {showTracks && results.tracks.length > 0 && (
              <motion.div key="tracks" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-3">
                <h2 className="text-sm font-semibold text-zinc-500 uppercase tracking-wider flex items-center gap-2">
                  <Music2 className="w-4 h-4" /> Tracks
                </h2>
                <div className="grid gap-2">
                  {results.tracks.map((track, i) => (
                    <motion.div
                      key={track.track_id}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: i * 0.02 }}
                      className="rounded-xl bg-surface-card border border-border-subtle hover:border-gem-500/30 transition-all overflow-hidden"
                    >
                      <div className="flex items-center gap-4 px-4 py-3">
                        <div className="w-8 h-8 rounded-lg bg-gem-500/10 flex items-center justify-center text-gem-400 text-xs font-bold">
                          {i + 1}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-zinc-200 truncate">{track.track_name}</p>
                          <p className="text-xs text-zinc-500 truncate">
                            {track.artist_name} {track.album_name ? `· ${track.album_name}` : ''}
                          </p>
                        </div>
                        {track.track_genre && (
                          <span className="text-xs px-2 py-0.5 rounded-md bg-surface text-zinc-500 border border-border-subtle hidden sm:inline">
                            {track.track_genre}
                          </span>
                        )}
                        <div className="hidden md:flex items-center gap-3 text-xs text-zinc-500">
                          <span title="Popularity" className="flex items-center gap-1">
                            <Zap className="w-3 h-3 text-amber-400" /> {track.popularity}
                          </span>
                          <span title="Danceability">{(track.danceability * 100).toFixed(0)}%</span>
                          <span title="Energy">{(track.energy * 100).toFixed(0)}%</span>
                          <span title="Tempo" className="w-14">{track.tempo.toFixed(0)} BPM</span>
                        </div>
                        <button
                          onClick={() => useAsReference(track)}
                          className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-gem-500/10 border border-gem-500/20 text-gem-400 text-xs font-medium hover:bg-gem-500/20 transition-all shrink-0"
                        >
                          <ChevronRight className="w-3 h-3" /> Use
                        </button>
                      </div>
                      {track.lyrics && (
                        <div className="px-4 pb-3">
                          <button
                            onClick={() => toggleLyrics(track.track_id)}
                            className="text-xs text-zinc-500 hover:text-zinc-300 transition-colors flex items-center gap-1"
                          >
                            <FileText className="w-3 h-3" />
                            {expandedLyrics.has(track.track_id) ? 'Hide lyrics' : 'Show lyrics'}
                          </button>
                          <AnimatePresence>
                            {expandedLyrics.has(track.track_id) && (
                              <motion.div
                                initial={{ height: 0, opacity: 0 }}
                                animate={{ height: 'auto', opacity: 1 }}
                                exit={{ height: 0, opacity: 0 }}
                                className="overflow-hidden"
                              >
                                <div className="mt-2 text-xs text-zinc-400 leading-relaxed max-h-40 overflow-y-auto whitespace-pre-wrap bg-surface rounded-lg p-3">
                                  {track.lyrics}
                                </div>
                              </motion.div>
                            )}
                          </AnimatePresence>
                        </div>
                      )}
                    </motion.div>
                  ))}
                </div>
              </motion.div>
            )}

            {showLyrics && results.lyrics.length > 0 && (
              <motion.div key="lyrics" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-3">
                <h2 className="text-sm font-semibold text-zinc-500 uppercase tracking-wider flex items-center gap-2">
                  <FileText className="w-4 h-4" /> Lyrics
                </h2>
                <div className="grid gap-2">
                  {results.lyrics.map((lyric, i) => (
                    <motion.div
                      key={lyric.track_id}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: i * 0.02 }}
                      className="rounded-xl bg-surface-card border border-border-subtle p-4 space-y-2 hover:border-gem-500/30 transition-all"
                    >
                      <div className="flex items-center justify-between">
                        <div className="min-w-0">
                          <p className="text-sm font-medium text-zinc-200 truncate">{lyric.track}</p>
                          <p className="text-xs text-zinc-500">{lyric.artist}</p>
                        </div>
                        <button
                          onClick={() => useLyricsAsReference(lyric)}
                          className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-gem-500/10 border border-gem-500/20 text-gem-400 text-xs font-medium hover:bg-gem-500/20 transition-all shrink-0"
                        >
                          <ChevronRight className="w-3 h-3" /> Use
                        </button>
                      </div>
                      <div className="text-xs text-zinc-400 leading-relaxed max-h-24 overflow-y-auto whitespace-pre-wrap bg-surface rounded-lg p-3">
                        {lyric.text.slice(0, 500)}{lyric.text.length > 500 ? '...' : ''}
                      </div>
                    </motion.div>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {!results.tracks.length && !results.artists.length && !results.lyrics.length && (
            <div className="text-center py-16 text-zinc-500">
              <Music2 className="w-12 h-12 mx-auto mb-3 text-zinc-700" />
              <p>No results found. Try a different search.</p>
            </div>
          )}
        </div>
      )}

      {!loading && !results && (
        <div className="text-center py-16 text-zinc-500">
          <Globe className="w-16 h-16 mx-auto mb-4 text-zinc-700" />
          <p className="text-lg mb-2">Search the music database</p>
          <p className="text-sm">Try: "Bad Bunny", "reggaeton", "Despacito", or lyrics phrases</p>
        </div>
      )}
    </div>
  )
}
