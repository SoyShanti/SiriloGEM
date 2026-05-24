export const API_BASE = '/api/v1'

export async function fetchAPI<T>(path: string, options?: RequestInit): Promise<T> {
  const { headers: customHeaders, ...restOptions } = options || {}
  const res = await fetch(`${API_BASE}${path}`, {
    ...restOptions,
    headers: { 'Content-Type': 'application/json', ...customHeaders },
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    if (Array.isArray(err.detail)) {
      const msgs = err.detail.map((e: { msg?: string; loc?: (string|number)[]; type?: string }) => {
        const field = e.loc?.slice(1).join('.') || '?'
        return `${field}: ${e.msg || e.type || 'invalid'}`
      })
      throw new Error(msgs.join('; '))
    }
    throw new Error(typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail) || res.statusText)
  }
  return res.json()
}

export type VoiceType = 'male' | 'female' | 'duet' | 'instrumental' | 'male_female' | 'female_male'
export type BackingVocals = 'none' | 'harmony' | 'call_response' | 'choir'
export type BackingVocalStyle = 'higher_third' | 'fifth_above' | 'falsetto' | 'same_octave'
export type LyricsLanguage = 'en' | 'es' | 'pt' | 'ja' | 'zh' | 'fr' | 'de' | 'it' | 'ko'

export interface StatusResponse {
  lm_studio: {
    available: boolean
    models: { id: string }[]
    active_model?: string
    active_profile?: { family: string; json_reliability: string } | null
  }
  ace_step: { loaded: boolean; api_url: string }
  knowledge_base: { ready: boolean; stats: Record<string, unknown> }
}

export interface ReferenceTrack {
  track_name: string
  artist_name: string
  similarity_score: number
  danceability: number
  energy: number
  valence: number
  tempo: number
  key?: number
  mode?: number
  speechiness?: number
  acousticness?: number
  instrumentalness?: number
  time_signature?: number
}

export interface ReferenceTrackWithSelection extends ReferenceTrack {
  track_id: string
  track_genre?: string
  popularity: number
  duration_ms?: number
  loudness?: number
  liveness?: number
  combined_score: number
  has_lyrics: boolean
  selected: boolean
  ref_role?: string
  ref_weight?: number
  surprise_element?: string
}

export interface LyricSample {
  artist: string
  track: string
  text: string
}

export interface PipelineTrace {
  reference_tracks: ReferenceTrack[]
  lyrics_samples: LyricSample[]
  hit_profile_used?: Record<string, unknown>
  lm_prompt?: string
  lm_params?: {
    bpm: number
    key_scale: string
    time_signature: string
    lyrics_template?: string
    song_structure?: string
  }
  comparison?: {
    closest_match?: { track_name: string; artist_name: string; similarity_score: number }
    differences: string[]
    overall_similarity: number
  }
  ref_result?: { found: boolean; ref_type: string; ref_name: string } | null
}

export interface GenerateRequest {
  prompt: string
  genre?: string
  mood?: string
  lyrics?: string
  use_hit_profile?: boolean
  duration_seconds?: number
  reference_track_ids?: string[]
  voice_type?: VoiceType
  backing_vocals?: BackingVocals
  backing_vocal_style?: BackingVocalStyle
  lyrics_language?: LyricsLanguage
  generate_lyrics?: boolean
  bpm?: number
  key_scale?: string
  time_signature?: string
  song_structure?: string
  optimized_prompt?: string
}

export interface GenerateResponse {
  id: number
  audio_path: string
  prompt: string
  genre?: string
  hit_prediction_score: number
  hit_prediction_label?: string
  pipeline_trace?: PipelineTrace
  message: string
}

export interface OptimizePromptRequest {
  prompt: string
  genre?: string
  mood?: string
  voice_type?: VoiceType
}

export interface OptimizePromptResponse {
  original_prompt: string
  optimized_prompt: string
  bpm: number
  key_scale: string
  time_signature: string
  song_structure: string
  mood: string
  reference_tracks: ReferenceTrackWithSelection[]
  ref_found: boolean
  ref_type?: string
  ref_name?: string
  auto_params?: Record<string, unknown>
  expanded_artists?: string[]
}

export interface ArtistSearchResult {
  name: string
  track_count: number
  lyrics_count: number
  genres: string[]
  top_genres: { genre: string; count: number }[]
}

export interface ArtistStats {
  artist_name: string
  track_count: number
  lyrics_count: number
  avg_bpm: number
  dominant_key: number
  dominant_mode: number
  avg_duration_ms: number
  derived_mood: string
  dominant_genre: string
  top_genres: { genre: string; count: number }[]
  avg_features: Record<string, number>
}

export interface OptimizePromptArtistRequest {
  primary_artist: string
  secondary_artists: string[]
  language: string
  voice_type?: string
  custom_prompt?: string
  genre_override?: string
}

export interface ComposeLyricsRequest {
  prompt: string
  selected_track_ids: string[]
  genre?: string
  mood?: string
  voice_type?: VoiceType
  backing_vocals?: BackingVocals
  lyrics_language?: LyricsLanguage
}

export interface ComposeLyricsResponse {
  lyrics: string
  reference_count: number
}

export interface ModelProfileInfo {
  model_id: string
  display_name: string
  family: string
  context_window: number
  max_output_tokens: number
  optimal_temperature: number
  json_reliability: string
  instruction_following: string
  needs_json_reinforcement: boolean
  needs_simple_prompts: boolean
  supports_system_prompt: boolean
  tested_at: string
  auto_detected: boolean
}

export interface TrackSchema {
  track_id: string
  artist_name: string
  track_name: string
  album_name?: string
  track_genre?: string
  popularity: number
  danceability: number
  energy: number
  valence: number
  tempo: number
  loudness: number
  key?: number
  mode?: number
  speechiness?: number
  acousticness?: number
  instrumentalness?: number
  liveness?: number
  time_signature?: number
  is_popular?: boolean
  hit_score?: number
  lyrics?: string
}

export interface HitProfileSchema {
  genre: string
  era?: string
  avg_danceability: number
  avg_energy: number
  avg_valence: number
  avg_tempo: number
  avg_loudness: number
  avg_speechiness: number
  avg_acousticness: number
  avg_instrumentalness: number
  avg_liveness: number
  sample_size: number
  avg_popularity: number
}

export interface HitPredictionRequest {
  danceability: number
  energy: number
  valence: number
  tempo: number
  loudness: number
  speechiness?: number
  acousticness?: number
  instrumentalness?: number
  liveness?: number
  genre?: string
}

export interface HitPredictionResponse {
  hit_score: number
  hit_label: string
  confidence: number
  recommendations: string[]
  ai_analysis?: string
}

export interface ArtistResultSchema {
  name: string
  track_count: number
  avg_popularity: number
  avg_danceability: number
  avg_energy: number
}

export interface LyricsResultSchema {
  track_id: string
  artist: string
  track: string
  text: string
}

export interface FullSearchResponse {
  tracks: TrackSchema[]
  artists: ArtistResultSchema[]
  lyrics: LyricsResultSchema[]
  total: number
}

export const api = {
  getStatus: () => fetchAPI<StatusResponse>('/status'),
  getTrack: (id: number) => fetchAPI<GenerateResponse>(`/tracks/${id}`),
  generate: (req: GenerateRequest) => fetchAPI<GenerateResponse>('/generate', { method: 'POST', body: JSON.stringify(req) }),
  searchTracks: (req: Record<string, unknown>) => fetchAPI<TrackSchema[]>('/search-tracks', { method: 'POST', body: JSON.stringify(req) }),
  fullSearch: (req: { query: string; search_type?: string; genre?: string; limit?: number; offset?: number }) =>
    fetchAPI<FullSearchResponse>('/search', { method: 'POST', body: JSON.stringify(req) }),
  getGenres: () => fetchAPI<{ genres: string[] }>('/genres'),
  getMoods: () => fetchAPI<{ moods: string[]; features: Record<string, Record<string, number>> }>('/moods'),
  getGenreAliases: () => fetchAPI<{ aliases: Record<string, string> }>('/genre-aliases'),
  getHitProfiles: () => fetchAPI<{ profiles: HitProfileSchema[] | Record<string, HitProfileSchema>; count: number }>('/hit-profiles'),
  getHitProfile: (genre: string) => fetchAPI<HitProfileSchema>(`/hit-profiles/${encodeURIComponent(genre)}`),
  predictHit: (req: HitPredictionRequest) => fetchAPI<HitPredictionResponse>('/predict-hit', { method: 'POST', body: JSON.stringify(req) }),
  getStats: () => fetchAPI<Record<string, unknown>>('/stats'),
  loadAceStep: () => fetchAPI<{ status: string; api_url: string }>('/load-ace-step', { method: 'POST' }),
  optimizePrompt: (req: OptimizePromptRequest) =>
    fetchAPI<OptimizePromptResponse>('/optimize-prompt', { method: 'POST', body: JSON.stringify(req) }),
  optimizePromptArtist: (req: OptimizePromptArtistRequest) =>
    fetchAPI<OptimizePromptResponse>('/optimize-prompt-artist', { method: 'POST', body: JSON.stringify(req) }),
  searchArtists: (q: string, lang?: string) =>
    fetchAPI<ArtistSearchResult[]>(`/search-artists?q=${encodeURIComponent(q)}&lang=${lang || 'en'}`),
  getArtistStats: (name: string, lang?: string) =>
    fetchAPI<ArtistStats>(`/artist-stats?name=${encodeURIComponent(name)}&lang=${lang || 'en'}`),
  composeLyrics: (req: ComposeLyricsRequest) =>
    fetchAPI<ComposeLyricsResponse>('/compose-lyrics', { method: 'POST', body: JSON.stringify(req) }),
  getModelProfiles: () =>
    fetchAPI<{ profiles: ModelProfileInfo[]; active_model?: string }>('/model-profiles'),
}
