from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class GenreEnum(str, Enum):
    pop = "pop"
    rock = "rock"
    hip_hop = "hip hop"
    r_and_b = "r&b"
    dance_electronic = "dance/electronic"
    latin = "latin"
    country = "country"
    metal = "metal"
    acoustic = "acoustic"
    indie = "indie"
    k_pop = "k-pop"
    reggaeton = "reggaeton"


VOICE_TYPES = {"male", "female", "duet", "instrumental", "male_female", "female_male"}
BACKING_VOCALS = {"none", "harmony", "call_response", "choir"}
BACKING_VOCAL_STYLES = {"higher_third", "fifth_above", "falsetto", "same_octave"}
LYRICS_LANGUAGES = {"en", "es", "pt", "ja", "zh", "fr", "de", "it", "ko"}


class HitProfileSchema(BaseModel):
    genre: str
    era: Optional[str] = None
    avg_danceability: float
    avg_energy: float
    avg_valence: float
    avg_tempo: float
    avg_loudness: float
    avg_speechiness: float
    avg_acousticness: float
    avg_instrumentalness: float
    avg_liveness: float
    sample_size: int
    avg_popularity: float


class ReferenceTrack(BaseModel):
    track_name: str
    artist_name: str
    similarity_score: float
    danceability: float
    energy: float
    valence: float
    tempo: float
    key: Optional[int] = None
    mode: Optional[int] = None
    speechiness: Optional[float] = None
    acousticness: Optional[float] = None
    instrumentalness: Optional[float] = None
    time_signature: Optional[int] = None


class ReferenceTrackWithSelection(BaseModel):
    track_id: str = ""
    track_name: str
    artist_name: str
    track_genre: Optional[str] = None
    popularity: int = 0
    duration_ms: Optional[int] = None
    danceability: float = 0.5
    energy: float = 0.5
    valence: float = 0.5
    tempo: float = 120.0
    loudness: Optional[float] = None
    key: Optional[int] = None
    mode: Optional[int] = None
    speechiness: Optional[float] = None
    acousticness: Optional[float] = None
    instrumentalness: Optional[float] = None
    liveness: Optional[float] = None
    time_signature: Optional[int] = None
    similarity_score: float = 0.0
    combined_score: float = 0.0
    has_lyrics: bool = False
    selected: bool = False
    ref_role: str = "primary"
    ref_weight: float = 0.60
    surprise_element: Optional[str] = None


class LyricSample(BaseModel):
    artist: str
    track: str
    text: str


class PipelineTrace(BaseModel):
    reference_tracks: list[ReferenceTrack] = []
    lyrics_samples: list[LyricSample] = []
    hit_profile_used: Optional[dict] = None
    lm_prompt: Optional[str] = None
    lm_params: Optional[dict] = None
    comparison: Optional[dict] = None
    ref_result: Optional[dict] = None


class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=3, max_length=2000, description="Text description of the music to generate")
    genre: Optional[str] = Field(None, description="Target genre")
    mood: Optional[str] = Field(None, description="Target mood")
    lyrics: Optional[str] = Field(None, description="Custom lyrics for the song")
    use_hit_profile: bool = Field(True, description="Enhance prompt with hit profile data")
    duration_seconds: Optional[float] = Field(None, ge=10, le=600, description="Target duration in seconds")
    reference_track_ids: Optional[list[str]] = Field(None, description="Specific Spotify track IDs to use as references")
    voice_type: Optional[str] = Field(None, description="Voice type: male, female, duet, instrumental")
    backing_vocals: Optional[str] = Field(None, description="Backing vocals style")
    backing_vocal_style: Optional[str] = Field(None, description="Backing vocal harmony style")
    lyrics_language: Optional[str] = Field(None, description="Language for generated lyrics")
    generate_lyrics: bool = Field(False, description="Whether to auto-generate lyrics from references")
    bpm: Optional[int] = Field(None, description="BPM from optimize step (sent directly to ACE Step)")
    key_scale: Optional[str] = Field(None, description="Key/scale from optimize step")
    time_signature: Optional[str] = Field(None, description="Time signature from optimize step")
    song_structure: Optional[str] = Field(None, description="Song structure from optimize step")
    optimized_prompt: Optional[str] = Field(None, description="Enhanced prompt text from optimize step")

    def validated_voice_type(self) -> Optional[str]:
        if self.voice_type and self.voice_type not in VOICE_TYPES:
            raise ValueError(f"voice_type must be one of {VOICE_TYPES}")
        return self.voice_type

    def validated_backing_vocals(self) -> Optional[str]:
        if self.backing_vocals and self.backing_vocals not in BACKING_VOCALS:
            raise ValueError(f"backing_vocals must be one of {BACKING_VOCALS}")
        return self.backing_vocals

    def validated_backing_vocal_style(self) -> Optional[str]:
        if self.backing_vocal_style and self.backing_vocal_style not in BACKING_VOCAL_STYLES:
            raise ValueError(f"backing_vocal_style must be one of {BACKING_VOCAL_STYLES}")
        return self.backing_vocal_style

    def validated_lyrics_language(self) -> Optional[str]:
        if self.lyrics_language and self.lyrics_language not in LYRICS_LANGUAGES:
            raise ValueError(f"lyrics_language must be one of {LYRICS_LANGUAGES}")
        return self.lyrics_language


class GenerateResponse(BaseModel):
    id: int
    audio_path: str
    prompt: str
    genre: Optional[str] = None
    hit_prediction_score: float = 0.0
    hit_prediction_label: Optional[str] = None
    pipeline_trace: Optional[PipelineTrace] = None
    message: str = "Generation started"


class ArtistSearchResult(BaseModel):
    name: str
    track_count: int = 0
    lyrics_count: int = 0
    genres: list[str] = []
    top_genres: list[dict] = []


class ArtistStats(BaseModel):
    artist_name: str
    track_count: int = 0
    lyrics_count: int = 0
    avg_bpm: float = 120.0
    dominant_key: Optional[int] = None
    dominant_mode: Optional[int] = None
    avg_duration_ms: float = 0
    derived_mood: str = ""
    dominant_genre: str = ""
    top_genres: list[dict] = []
    avg_features: dict = {}


class OptimizePromptArtistRequest(BaseModel):
    primary_artist: str = Field(..., min_length=1)
    secondary_artists: list[str] = Field([], max_length=2)
    language: str = Field(..., pattern=r"^(en|es|pt)$")
    voice_type: Optional[str] = None
    custom_prompt: Optional[str] = None
    genre_override: Optional[str] = None

    def validated_voice_type(self) -> Optional[str]:
        if self.voice_type and self.voice_type not in VOICE_TYPES:
            raise ValueError(f"voice_type must be one of {VOICE_TYPES}")
        return self.voice_type


class OptimizePromptRequest(BaseModel):
    prompt: str = Field(..., min_length=3, max_length=2000)
    genre: Optional[str] = None
    mood: Optional[str] = None
    voice_type: Optional[str] = None

    def validated_voice_type(self) -> Optional[str]:
        if self.voice_type and self.voice_type not in VOICE_TYPES:
            raise ValueError(f"voice_type must be one of {VOICE_TYPES}")
        return self.voice_type


class OptimizePromptResponse(BaseModel):
    original_prompt: str
    optimized_prompt: str
    bpm: int = 120
    key_scale: str = "C major"
    time_signature: str = "4/4"
    song_structure: str = ""
    mood: str = ""
    reference_tracks: list[ReferenceTrackWithSelection] = []
    ref_found: bool = False
    ref_type: Optional[str] = None
    ref_name: Optional[str] = None
    auto_params: Optional[dict] = None
    expanded_artists: list[str] = []


class ComposeLyricsRequest(BaseModel):
    prompt: str = Field(..., min_length=3, max_length=4000)
    selected_track_ids: list[str] = Field(..., min_length=1, max_length=10)
    genre: Optional[str] = None
    mood: Optional[str] = None
    voice_type: Optional[str] = None
    backing_vocals: Optional[str] = None
    lyrics_language: Optional[str] = None

    def validated_voice_type(self) -> Optional[str]:
        if self.voice_type and self.voice_type not in VOICE_TYPES:
            raise ValueError(f"voice_type must be one of {VOICE_TYPES}")
        return self.voice_type

    def validated_backing_vocals(self) -> Optional[str]:
        if self.backing_vocals and self.backing_vocals not in BACKING_VOCALS:
            raise ValueError(f"backing_vocals must be one of {BACKING_VOCALS}")
        return self.backing_vocals

    def validated_lyrics_language(self) -> Optional[str]:
        if self.lyrics_language and self.lyrics_language not in LYRICS_LANGUAGES:
            raise ValueError(f"lyrics_language must be one of {LYRICS_LANGUAGES}")
        return self.lyrics_language


class ComposeLyricsResponse(BaseModel):
    lyrics: str
    reference_count: int = 0


class ModelProfileSchema(BaseModel):
    model_id: str
    display_name: str = ""
    family: str = ""
    context_window: int = 4096
    max_output_tokens: int = 2048
    optimal_temperature: float = 0.6
    json_reliability: str = "low"
    instruction_following: str = "low"
    needs_json_reinforcement: bool = True
    needs_simple_prompts: bool = True
    supports_system_prompt: bool = True
    tested_at: str = ""
    auto_detected: bool = False


class ModelProfileUpdateRequest(BaseModel):
    display_name: Optional[str] = None
    optimal_temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_output_tokens: Optional[int] = Field(None, ge=256, le=32768)
    json_reliability: Optional[str] = None
    instruction_following: Optional[str] = None
    needs_json_reinforcement: Optional[bool] = None
    needs_simple_prompts: Optional[bool] = None


class HitPredictionRequest(BaseModel):
    danceability: float = Field(..., ge=0, le=1)
    energy: float = Field(..., ge=0, le=1)
    valence: float = Field(..., ge=0, le=1)
    tempo: float = Field(..., ge=0, le=300)
    loudness: float = Field(..., ge=-60, le=5)
    speechiness: float = Field(0.05, ge=0, le=1)
    acousticness: float = Field(0.1, ge=0, le=1)
    instrumentalness: float = Field(0.0, ge=0, le=1)
    liveness: float = Field(0.1, ge=0, le=1)
    genre: Optional[str] = None


class HitPredictionResponse(BaseModel):
    hit_score: float
    hit_label: str
    confidence: float
    recommendations: list[str] = []


class TrackSearchRequest(BaseModel):
    genre: Optional[str] = None
    min_popularity: Optional[int] = Field(None, ge=0, le=100)
    min_danceability: Optional[float] = Field(None, ge=0, le=1)
    min_energy: Optional[float] = Field(None, ge=0, le=1)
    min_valence: Optional[float] = Field(None, ge=0, le=1)
    tempo_range: Optional[list[float]] = Field(None, min_length=2, max_length=2)
    limit: int = Field(20, ge=1, le=100)


class FullSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    search_type: Optional[str] = Field("all", description="all, track, artist, lyrics")
    genre: Optional[str] = None
    limit: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0)


class TrackSchema(BaseModel):
    track_id: str
    artist_name: str
    track_name: str
    album_name: Optional[str] = None
    track_genre: Optional[str] = None
    popularity: int
    danceability: float
    energy: float
    valence: float
    tempo: float
    loudness: float
    key: Optional[int] = None
    mode: Optional[int] = None
    speechiness: Optional[float] = None
    acousticness: Optional[float] = None
    instrumentalness: Optional[float] = None
    liveness: Optional[float] = None
    time_signature: Optional[int] = None
    is_popular: Optional[bool] = None
    hit_score: Optional[float] = None
    lyrics: Optional[str] = None


class ArtistResultSchema(BaseModel):
    name: str
    track_count: int
    avg_popularity: float
    avg_danceability: float
    avg_energy: float


class LyricsResultSchema(BaseModel):
    track_id: str
    artist: str
    track: str
    text: str


class FullSearchResponse(BaseModel):
    tracks: list[TrackSchema] = []
    artists: list[ArtistResultSchema] = []
    lyrics: list[LyricsResultSchema] = []
    total: int = 0


class LMStudioModelInfo(BaseModel):
    id: str
    object: str = "model"
    owned_by: str = "local"
