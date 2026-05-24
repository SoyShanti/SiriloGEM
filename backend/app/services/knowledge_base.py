import re
import logging
import numpy as np
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from backend.app.core.database import SessionLocal
from backend.app.models.tables import Track, Lyrics, HitProfile

logger = logging.getLogger("spotigem.knowledge_base")

MOOD_PRESETS = {
    "energetic": {"danceability": 0.8, "energy": 0.9, "valence": 0.6, "tempo": 140},
    "chill": {"danceability": 0.5, "energy": 0.3, "valence": 0.5, "tempo": 85},
    "hypnotic": {"danceability": 0.7, "energy": 0.6, "valence": 0.4, "tempo": 125},
    "driving": {"danceability": 0.7, "energy": 0.85, "valence": 0.5, "tempo": 135},
    "laid_back": {"danceability": 0.5, "energy": 0.25, "valence": 0.6, "tempo": 80},
    "dark": {"danceability": 0.5, "energy": 0.7, "valence": 0.2, "loudness": -12},
    "happy": {"danceability": 0.8, "energy": 0.8, "valence": 0.9, "tempo": 120},
    "sad": {"danceability": 0.4, "energy": 0.3, "valence": 0.2, "tempo": 90},
    "romantic": {"danceability": 0.6, "energy": 0.4, "valence": 0.7, "tempo": 95},
    "melancholic": {"danceability": 0.35, "energy": 0.3, "valence": 0.15, "tempo": 85},
    "euphoric": {"danceability": 0.9, "energy": 0.95, "valence": 0.95, "tempo": 140},
    "nostalgic": {"danceability": 0.5, "energy": 0.4, "valence": 0.5, "acousticness": 0.5, "tempo": 100},
    "brooding": {"danceability": 0.4, "energy": 0.5, "valence": 0.2, "tempo": 95},
    "dreamy": {"danceability": 0.4, "energy": 0.3, "valence": 0.6, "acousticness": 0.5, "tempo": 85},
    "aggressive": {"danceability": 0.5, "energy": 0.95, "valence": 0.15, "loudness": -4, "tempo": 150},
    "epic": {"danceability": 0.5, "energy": 0.85, "valence": 0.6, "tempo": 120},
    "groovy": {"danceability": 0.9, "energy": 0.7, "valence": 0.7, "tempo": 110},
    "intimate": {"danceability": 0.4, "energy": 0.3, "valence": 0.6, "acousticness": 0.6, "tempo": 80},
    "anthemic": {"danceability": 0.6, "energy": 0.8, "valence": 0.8, "tempo": 125},
    "ethereal": {"danceability": 0.3, "energy": 0.35, "valence": 0.5, "acousticness": 0.4, "instrumentalness": 0.5, "tempo": 90},
    "sensual": {"danceability": 0.7, "energy": 0.5, "valence": 0.7, "tempo": 100},
    "triumphant": {"danceability": 0.6, "energy": 0.85, "valence": 0.85, "tempo": 130},
    "club": {"danceability": 0.95, "energy": 0.85, "valence": 0.6, "tempo": 128},
    "afterparty": {"danceability": 0.7, "energy": 0.55, "valence": 0.6, "tempo": 110},
    "workout": {"danceability": 0.8, "energy": 0.95, "valence": 0.7, "tempo": 145},
    "study": {"danceability": 0.3, "energy": 0.2, "valence": 0.5, "instrumentalness": 0.8, "acousticness": 0.5, "tempo": 80},
    "road_trip": {"danceability": 0.7, "energy": 0.65, "valence": 0.75, "tempo": 115},
    "rainy_day": {"danceability": 0.3, "energy": 0.25, "valence": 0.3, "acousticness": 0.6, "tempo": 85},
    "summer": {"danceability": 0.85, "energy": 0.75, "valence": 0.85, "tempo": 120},
    "midnight": {"danceability": 0.5, "energy": 0.45, "valence": 0.3, "tempo": 100},
}

FEATURE_KEYS = ["danceability", "energy", "valence", "tempo", "loudness", "speechiness", "acousticness", "instrumentalness", "liveness"]

CROSS_GENRE_MAP = {
    "hip-hop": ["electronic", "jazz"],
    "rock": ["blues", "soul"],
    "electronic": ["hip-hop", "folk"],
    "pop": ["r&b", "indie"],
    "latin": ["jazz", "rock"],
    "r&b": ["hip-hop", "folk"],
    "folk": ["jazz", "electronic"],
    "jazz": ["hip-hop", "latin"],
    "metal": ["electronic", "rock"],
    "country": ["rock", "folk"],
    "indie": ["electronic", "folk"],
    "reggae": ["latin", "soul"],
    "soul": ["r&b", "latin"],
    "blues": ["rock", "jazz"],
}

SURPRISE_ELEMENTS = {
    "hip-hop": ["vintage jazz sample", "bossa nova chord progression", "classical string section"],
    "rock": ["synth wave pad", "hip-hop drum break", "soul horn section"],
    "electronic": ["acoustic guitar riff", "soul vocal chop", "classical piano arpeggio"],
    "pop": ["trap hi-hat pattern", "folk mandolin", "jazz chord substitution"],
    "latin": ["jazz piano montuno", "rock distorted guitar", "electronic synth bass"],
    "r&b": ["folk acoustic texture", "jazz harmony", "electronic ambient pad"],
    "folk": ["electronic ambient texture", "hip-hop beat pattern", "jazz vibraphone"],
    "jazz": ["hip-hop boom-bap beat", "latin percussion section", "electronic synth texture"],
    "metal": ["electronic industrial noise", "orchestral strings", "ambient drone"],
    "country": ["rock distortion pedal", "folk celtic whistle", "soul organ"],
    "indie": ["electronic glitch texture", "folk banjo", "jazz brushed drums"],
    "reggae": ["latin brass section", "soul falsetto vocal", "electronic dub effects"],
    "soul": ["latin percussion", "folk harmonica", "electronic synth bass"],
    "blues": ["jazz walking bass line", "rock overdrive", "soul gospel choir"],
}

STYLE_PATTERNS = [
    (r"\bestilo\s+(.+?)(?:$|[,;.!?])", "style"),
    (r"\bstyle\s+(.+?)(?:$|[,;.!?])", "style"),
    (r"\blike\s+(.+?)(?:$|[,;.!?])", "style"),
    (r"\bcomo\s+(.+?)(?:$|[,;.!?])", "style"),
    (r"\bsimilar\s+to\s+(.+?)(?:$|[,;.!?])", "style"),
    (r"\binspirad[oa]?\s+(?:en\s+)?(.+?)(?:$|[,;.!?])", "style"),
    (r"\binfluenced\s+by\s+(.+?)(?:$|[,;.!?])", "style"),
    (r"\bin\s+the\s+(?:style|vein)\s+of\s+(.+?)(?:$|[,;.!?])", "style"),
]


class KnowledgeBase:
    def __init__(self):
        self._ready = False
        self._hit_profiles: dict = {}
        self._genre_stats: dict = {}

    def is_ready(self) -> bool:
        return self._ready

    async def initialize(self):
        self._load_hit_profiles_cache()
        self._ready = True
        logger.info("Knowledge base ready")

    def _load_hit_profiles_cache(self):
        db = SessionLocal()
        try:
            profiles = db.query(HitProfile).all()
            for p in profiles:
                key = f"{p.genre}_{p.era or 'all'}"
                self._hit_profiles[key] = {
                    "genre": p.genre,
                    "era": p.era,
                    "avg_danceability": p.avg_danceability,
                    "avg_energy": p.avg_energy,
                    "avg_valence": p.avg_valence,
                    "avg_tempo": p.avg_tempo,
                    "avg_loudness": p.avg_loudness,
                    "avg_speechiness": p.avg_speechiness,
                    "avg_acousticness": p.avg_acousticness,
                    "avg_instrumentalness": p.avg_instrumentalness,
                    "avg_liveness": p.avg_liveness,
                    "sample_size": p.sample_size,
                    "avg_popularity": p.avg_popularity,
                }
        finally:
            db.close()

    def get_hit_profile(self, genre: str) -> Optional[dict]:
        return self._hit_profiles.get(f"{genre}_all")

    def get_all_hit_profiles(self) -> dict:
        return dict(self._hit_profiles)

    def search_by_reference(self, query: str) -> dict:
        p = query.lower().strip()
        result = {"found": False, "ref_type": None, "ref_name": None, "features": None, "artist_tracks": [], "ref_track": None, "genre_resolved": None, "artist_subgenres": []}

        for pattern, ptype in STYLE_PATTERNS:
            m = re.search(pattern, p, re.IGNORECASE)
            if m:
                ref_text = m.group(1).strip()
                found = self._try_resolve_reference(ref_text, result)
                if found:
                    return result
                break

        found = self._try_resolve_reference(p, result)
        if found:
            return result

        return result

    def _try_resolve_reference(self, ref_text: str, result: dict) -> bool:
        ref_text = ref_text.strip()
        if not ref_text:
            return False

        genre_match = self._find_genre_in_db(ref_text)
        if genre_match:
            result["found"] = True
            result["ref_type"] = "genre"
            result["ref_name"] = genre_match
            result["genre_resolved"] = genre_match
            profile = self.get_hit_profile(genre_match)
            if profile:
                result["features"] = {k: profile.get(f"avg_{k}", 0.5) for k in FEATURE_KEYS}
                result["features"]["tempo"] = profile.get("avg_tempo", 120)
                result["features"]["loudness"] = profile.get("avg_loudness", -8)
            return True

        artist_match = self._find_artist(ref_text)
        if artist_match:
            result["found"] = True
            result["ref_type"] = "artist"
            result["ref_name"] = artist_match
            avg = self.get_artist_avg_features(artist_match)
            if avg:
                result["features"] = avg
            artist_tracks = self.get_artist_tracks(artist_match, limit=10)
            result["artist_tracks"] = artist_tracks
            genre = self._resolve_genre_from_tracks(artist_tracks)
            if genre:
                result["genre_resolved"] = genre
                result["artist_subgenres"] = list({t.get("track_genre") for t in artist_tracks if t.get("track_genre")})
            return True

        track_match = self._find_track_by_name(ref_text)
        if track_match:
            result["found"] = True
            result["ref_type"] = "track"
            result["ref_name"] = f"{track_match['track_name']} by {track_match['artist_name']}"
            result["ref_track"] = track_match
            result["features"] = {k: track_match.get(k, 0.5) for k in FEATURE_KEYS}
            artist_tracks = self.get_artist_tracks(track_match["artist_name"], limit=5)
            result["artist_tracks"] = artist_tracks
            raw_genre = track_match.get("track_genre")
            if raw_genre:
                result["genre_resolved"] = raw_genre
                result["artist_subgenres"] = list({t.get("track_genre") for t in artist_tracks if t.get("track_genre")} | {raw_genre})
            return True

        return False

    def get_track_by_id(self, track_id: str) -> Optional[dict]:
        db = SessionLocal()
        try:
            track = db.query(Track).filter(Track.track_id == track_id).first()
            if track:
                return self._track_to_dict(track)
            return None
        finally:
            db.close()

    def _find_genre_in_db(self, text: str) -> Optional[str]:
        t = text.lower().strip()
        db = SessionLocal()
        try:
            all_genres = db.query(Track.track_genre).distinct().filter(Track.track_genre.isnot(None)).all()
            genre_names = {r[0].lower(): r[0] for r in all_genres if r[0]}
            if t in genre_names:
                return genre_names[t]
            aliases = {
                "hip hop": "hip-hop", "hiphop": "hip-hop", "rap": "hip-hop", "trap": "hip-hop",
                "rnb": "r&b", "r and b": "r&b", "rhythm and blues": "r&b",
                "edm": "electronic", "electronica": "electronic", "dance": "electronic",
                "punk": "rock", "punk rock": "rock", "pop punk": "rock", "alt rock": "rock",
                "grunge": "rock", "emo": "rock", "hard rock": "rock",
                "cuarteto": "latin", "reggaeton": "latin", "cumbia": "latin",
                "bachata": "latin", "salsa": "latin", "samba": "latin",
                "sertanejo": "latin", "mpb": "latin", "bossa nova": "latin",
                "folk": "folk", "singer-songwriter": "folk",
                "soul": "soul", "funk": "soul",
                "blues": "blues",
                "jazz": "jazz",
                "metal": "metal", "heavy metal": "metal",
                "indie": "indie", "indie rock": "indie",
                "country": "country",
                "reggae": "reggae",
            }
            resolved = aliases.get(t)
            if resolved and resolved in genre_names:
                return genre_names[resolved]
            for alias_key, canonical in aliases.items():
                if alias_key in t and canonical in genre_names:
                    return genre_names[canonical]
            return None
        finally:
            db.close()

    def _resolve_genre_from_tracks(self, tracks: list[dict]) -> Optional[str]:
        if not tracks:
            return None
        genre_weighted: dict[str, float] = {}
        for t in tracks:
            g = t.get("track_genre")
            if g:
                genre_weighted[g] = genre_weighted.get(g, 0) + 1
        if not genre_weighted:
            return None
        sorted_genres = sorted(genre_weighted.items(), key=lambda x: x[1], reverse=True)
        return sorted_genres[0][0]

    def _find_track_by_name(self, name: str) -> Optional[dict]:
        db = SessionLocal()
        try:
            variants = [name]
            if " " in name:
                variants.append(name.replace(" ", "-"))
            if "-" in name:
                variants.append(name.replace("-", " "))
            for variant in variants:
                track = db.query(Track).filter(
                    Track.track_name.ilike(f"%{variant}%")
                ).limit(10).all()
                if track:
                    best = max(track, key=lambda t: t.popularity or 0)
                    return self._track_to_dict(best)
            return None
        finally:
            db.close()

    def _find_artist(self, name: str) -> Optional[str]:
        db = SessionLocal()
        try:
            first_artist = name.split(",")[0].split(";")[0].strip()
            variants = [first_artist]
            if " " in first_artist:
                variants.append(first_artist.replace(" ", "-"))
            if "-" in first_artist:
                variants.append(first_artist.replace("-", " "))
            for variant in variants:
                track = db.query(Track).filter(
                    Track.artist_name.ilike(f"%{variant}%")
                ).first()
                if track:
                    return track.artist_name
            return None
        finally:
            db.close()

    def get_artist_tracks(self, artist_name: str, limit: int = 10) -> list[dict]:
        db = SessionLocal()
        try:
            clean = artist_name.split(",")[0].split(";")[0].strip()
            tracks = db.query(Track).filter(
                Track.artist_name.ilike(f"%{clean}%")
            ).limit(limit * 3).all()
            tracks.sort(key=lambda t: t.popularity or 0, reverse=True)
            return [self._track_to_dict(t) for t in tracks[:limit]]
        finally:
            db.close()

    def get_artist_avg_features(self, artist_name: str) -> Optional[dict]:
        db = SessionLocal()
        try:
            clean = artist_name.split(",")[0].split(";")[0].strip()
            row = db.execute(text("""
                SELECT AVG(danceability), AVG(energy), AVG(valence), AVG(tempo),
                       AVG(loudness), AVG(speechiness), AVG(acousticness),
                       AVG(instrumentalness), AVG(liveness)
                FROM tracks
                WHERE artist_name LIKE :artist
            """), {"artist": f"%{clean}%"}).fetchone()
            if row and row[0] is not None:
                return {
                    "danceability": float(row[0]),
                    "energy": float(row[1]),
                    "valence": float(row[2]),
                    "tempo": float(row[3]),
                    "loudness": float(row[4]),
                    "speechiness": float(row[5]),
                    "acousticness": float(row[6]),
                    "instrumentalness": float(row[7]),
                    "liveness": float(row[8]),
                }
            return None
        finally:
            db.close()

    def _track_to_dict(self, t: Track) -> dict:
        return {
            "track_id": t.track_id,
            "artist_name": t.artist_name,
            "track_name": t.track_name,
            "album_name": t.album_name,
            "track_genre": t.track_genre,
            "popularity": t.popularity,
            "duration_ms": t.duration_ms,
            "danceability": t.danceability,
            "energy": t.energy,
            "valence": t.valence,
            "tempo": t.tempo,
            "loudness": t.loudness,
            "key": t.key,
            "mode": t.mode,
            "speechiness": t.speechiness,
            "acousticness": t.acousticness,
            "instrumentalness": t.instrumentalness,
            "liveness": t.liveness,
            "time_signature": t.time_signature,
            "is_popular": t.is_popular,
        }

    def search_tracks(self, genre: Optional[str] = None, min_danceability: float = 0.0, min_energy: float = 0.0, min_valence: float = 0.0, tempo_range: Optional[tuple] = None, limit: int = 20) -> list[dict]:
        db = SessionLocal()
        try:
            query = db.query(Track)
            if genre:
                query = query.filter(Track.track_genre == genre)
            if min_danceability > 0:
                query = query.filter(Track.danceability >= min_danceability)
            if min_energy > 0:
                query = query.filter(Track.energy >= min_energy)
            if min_valence > 0:
                query = query.filter(Track.valence >= min_valence)
            if tempo_range:
                query = query.filter(Track.tempo >= tempo_range[0], Track.tempo <= tempo_range[1])
            query = query.limit(limit)
            return [self._track_to_dict(t) for t in query.all()]
        finally:
            db.close()

    def full_search(self, query: str, search_type: str = "all", genre: Optional[str] = None, limit: int = 20, offset: int = 0) -> dict:
        db = SessionLocal()
        try:
            results = {"tracks": [], "artists": [], "lyrics": [], "total": 0}
            q = f"%{query.strip()}%"

            if search_type in ("all", "track"):
                q_tracks = db.query(Track).filter(
                    (Track.track_name.ilike(q)) | (Track.artist_name.ilike(q))
                )
                if genre:
                    q_tracks = q_tracks.filter(Track.track_genre == genre)
                results["total"] += q_tracks.count()
                tracks = q_tracks.offset(offset).limit(limit).all()
                results["tracks"] = [self._track_to_dict(t) for t in tracks]

            if search_type in ("all", "artist"):
                artist_rows = db.query(
                    Track.artist_name,
                    func.count(Track.id).label("track_count"),
                    func.avg(Track.danceability).label("avg_danceability"),
                    func.avg(Track.energy).label("avg_energy"),
                ).filter(
                    Track.artist_name.ilike(q)
                ).group_by(Track.artist_name).offset(offset).limit(limit).all()
                results["artists"] = [
                    {
                        "name": r[0],
                        "track_count": r[1],
                        "avg_danceability": round(float(r[2] or 0), 3),
                        "avg_energy": round(float(r[3] or 0), 3),
                    }
                    for r in artist_rows
                ]

            if search_type in ("all", "lyrics"):
                q_lyrics = db.query(Lyrics).filter(
                    (Lyrics.artist_name.ilike(q)) | (Lyrics.track_name.ilike(q))
                )
                lyrics_rows = q_lyrics.offset(offset).limit(limit).all()
                results["lyrics"] = [
                    {
                        "track_id": l.track_id,
                        "artist": l.artist_name,
                        "track": l.track_name,
                        "text": l.lyrics_text[:500] if l.lyrics_text else "",
                    }
                    for l in lyrics_rows
                ]

            return results
        finally:
            db.close()

    def get_lyrics_for_track(self, artist_name: str, track_name: str, track_id: Optional[str] = None) -> Optional[dict]:
        db = SessionLocal()
        try:
            if track_id:
                lyric = db.query(Lyrics).filter(Lyrics.track_id == track_id).first()
                if lyric and lyric.lyrics_text:
                    return {"track_id": track_id, "artist": lyric.artist_name, "track": lyric.track_name, "text": lyric.lyrics_text[:2000]}
            clean_artist = artist_name.split(",")[0].split(";")[0].strip()
            lyric = db.query(Lyrics).filter(
                Lyrics.artist_name.ilike(f"%{clean_artist}%"),
                Lyrics.track_name.ilike(f"%{track_name.strip()}%")
            ).first()
            if lyric and lyric.lyrics_text:
                return {"track_id": track_id, "artist": lyric.artist_name, "track": lyric.track_name, "text": lyric.lyrics_text[:2000]}
            lyric = db.query(Lyrics).filter(
                Lyrics.artist_name.ilike(f"%{clean_artist}%")
            ).first()
            if lyric and lyric.lyrics_text:
                return {"track_id": track_id, "artist": lyric.artist_name, "track": lyric.track_name, "text": lyric.lyrics_text[:2000]}
            return None
        finally:
            db.close()

    def get_similar_tracks(self, features: dict, genre: Optional[str] = None, limit: int = 5) -> list[dict]:
        db = SessionLocal()
        try:
            query = db.query(Track)
            if genre:
                query = query.filter(Track.track_genre == genre)
            tracks = query.limit(200).all()
            if not tracks:
                return []

            target = np.array([features.get(k, 0.5) for k in FEATURE_KEYS])
            target[3] /= 200.0
            target[4] = abs(target[4]) / 60.0

            scored = []
            for t in tracks:
                vec = np.array([
                    t.danceability or 0.5, t.energy or 0.5, t.valence or 0.5,
                    (t.tempo or 120) / 200.0, abs(t.loudness or -6) / 60.0,
                    t.speechiness or 0.05, t.acousticness or 0.1,
                    t.instrumentalness or 0.0, t.liveness or 0.1
                ])
                dist = float(np.linalg.norm(vec - target))
                scored.append((dist, t))

            scored.sort(key=lambda x: x[0])
            return [
                {
                    "track_id": t.track_id, "artist_name": t.artist_name,
                    "track_name": t.track_name, "track_genre": t.track_genre,
                    "popularity": t.popularity, "duration_ms": t.duration_ms,
                    "danceability": t.danceability, "energy": t.energy,
                    "valence": t.valence, "tempo": t.tempo, "loudness": t.loudness,
                    "key": t.key, "mode": t.mode,
                    "speechiness": t.speechiness, "acousticness": t.acousticness,
                    "instrumentalness": t.instrumentalness, "liveness": t.liveness,
                    "time_signature": t.time_signature,
                    "similarity_score": round(1.0 - min(d, 2.0) / 2.0, 3),
                }
                for d, t in scored[:limit]
            ]
        finally:
            db.close()

    def get_lyrics_by_genre(self, genre: str, limit: int = 3) -> list[dict]:
        db = SessionLocal()
        try:
            results = []
            track_ids = [r[0] for r in db.query(Track.track_id).filter(
                Track.track_genre == genre, Track.track_id.isnot(None)
            ).limit(limit * 10).all()]

            if track_ids:
                for tid in track_ids:
                    lyrics = db.query(Lyrics).filter(Lyrics.track_id == tid).first()
                    if lyrics and lyrics.lyrics_text:
                        results.append({"track_id": tid, "artist": lyrics.artist_name, "track": lyrics.track_name, "text": lyrics.lyrics_text[:2000]})
                        if len(results) >= limit:
                            break

            if not results and track_ids:
                for tid in track_ids:
                    track = db.query(Track).filter(Track.track_id == tid).first()
                    if track:
                        lyrics = db.query(Lyrics).filter(
                            Lyrics.artist_name.ilike(f"%{track.artist_name.split(',')[0].strip()}%")
                        ).first()
                        if lyrics and lyrics.lyrics_text:
                            results.append({"track_id": tid, "artist": lyrics.artist_name, "track": lyrics.track_name, "text": lyrics.lyrics_text[:2000]})
                            if len(results) >= limit:
                                break
            return results
        finally:
            db.close()

    def get_lyrics_by_tracks(self, tracks: list[dict], limit: int = 5) -> list[dict]:
        results = []
        for t in tracks[:limit * 3]:
            artist = t.get("artist_name", "")
            track_name = t.get("track_name", "")
            track_id = t.get("track_id")
            if not artist:
                continue
            lyric = self.get_lyrics_for_track(artist, track_name, track_id=track_id)
            if lyric:
                results.append(lyric)
                if len(results) >= limit:
                    break
        return results

    def get_reference_tracks(self, features: dict, genre: Optional[str] = None,
                             artist_tracks: list[dict] = [], artist_subgenres: list[str] = [],
                             limit: int = 10) -> tuple[list[dict], Optional[str]]:
        db = SessionLocal()
        try:
            artist_ids = {at.get("track_id") for at in artist_tracks if at.get("track_id")}
            query = db.query(Track)
            if genre:
                query = query.filter(Track.track_genre == genre)
            candidates = query.order_by(Track.year.desc()).limit(500).all()
            if not candidates and genre:
                candidates = db.query(Track).order_by(Track.year.desc()).limit(500).all()

            subgenre_set = {g.lower() for g in artist_subgenres} if artist_subgenres else set()

            target = np.array([features.get(k, 0.5) for k in FEATURE_KEYS])
            target[3] /= 200.0
            target[4] = abs(target[4]) / 60.0

            scored = []
            for t in candidates:
                tid = t.track_id or f"track_{t.id}"
                if tid in artist_ids:
                    continue
                vec = np.array([
                    t.danceability or 0.5, t.energy or 0.5, t.valence or 0.5,
                    (t.tempo or 120) / 200.0, abs(t.loudness or -6) / 60.0,
                    t.speechiness or 0.05, t.acousticness or 0.1,
                    t.instrumentalness or 0.0, t.liveness or 0.1
                ])
                dist = float(np.linalg.norm(vec - target))
                similarity = max(0, 1.0 - min(dist, 2.0) / 2.0)
                combined = 0.4 * similarity + 0.6 * 0.5
                in_subgenre = (t.track_genre or "").lower() in subgenre_set
                if in_subgenre:
                    combined = min(1.0, combined + 0.35)
                elif subgenre_set and (t.track_genre or "").lower() not in subgenre_set:
                    combined *= 0.6
                scored.append((combined, t, tid, similarity))

            scored.sort(key=lambda x: x[0], reverse=True)

            primary_count = max(1, int(limit * 0.6))
            contrast_count = max(1, int(limit * 0.3))
            surprise_count = max(1, limit - primary_count - contrast_count)

            all_ids = set()
            for at in artist_tracks:
                tid = at.get("track_id") or ""
                if tid:
                    all_ids.add(tid)
            for _, _, tid, _ in scored[:limit]:
                all_ids.add(tid)

            contrast_genre = None
            cross_genres = []
            if genre and genre in CROSS_GENRE_MAP:
                cross_genres = CROSS_GENRE_MAP[genre]

            if cross_genres:
                for cg in cross_genres:
                    contrast_track = db.query(Track).filter(
                        Track.track_genre == cg
                    ).order_by(Track.year.desc()).limit(50).first()
                    if contrast_track:
                        ctid = contrast_track.track_id or f"track_{contrast_track.id}"
                        all_ids.add(ctid)
                        contrast_genre = cg
                        break

            lyrics_count = {}
            if all_ids:
                for row in db.query(Lyrics.track_id).filter(
                    Lyrics.track_id.in_(list(all_ids))
                ).all():
                    lyrics_count[row[0]] = True

            artist_results = []
            for at in artist_tracks:
                tid = at.get("track_id") or ""
                if tid:
                    at["has_lyrics"] = tid in lyrics_count
                    at["selected"] = True
                    at["combined_score"] = at.get("combined_score", 0.90)
                    at["similarity_score"] = at.get("similarity_score", 0.85)
                    at["ref_role"] = "primary"
                    at["ref_weight"] = 0.60
                    artist_results.append(at)

            db_results = []
            for i, (combined, t, tid, similarity) in enumerate(scored[:limit]):
                has_lyrics = tid in lyrics_count
                if i < primary_count:
                    role, weight = "primary", 0.60
                elif i < primary_count + contrast_count:
                    role, weight = "contrast", 0.30
                else:
                    role, weight = "surprise", 0.10
                db_results.append({
                    "track_id": tid,
                    "artist_name": t.artist_name,
                    "track_name": t.track_name,
                    "track_genre": t.track_genre,
                    "popularity": t.popularity,
                    "duration_ms": t.duration_ms,
                    "danceability": t.danceability,
                    "energy": t.energy,
                    "valence": t.valence,
                    "tempo": t.tempo,
                    "loudness": t.loudness,
                    "key": t.key,
                    "mode": t.mode,
                    "speechiness": t.speechiness,
                    "acousticness": t.acousticness,
                    "instrumentalness": t.instrumentalness,
                    "liveness": t.liveness,
                    "time_signature": t.time_signature,
                    "similarity_score": round(similarity, 3),
                    "combined_score": round(combined, 3),
                    "has_lyrics": has_lyrics,
                    "selected": i < max(0, 5 - len(artist_results)),
                    "ref_role": role,
                    "ref_weight": weight,
                })

            results = artist_results + db_results

            if contrast_genre and cross_genres:
                for cg in cross_genres:
                    contrast_track = db.query(Track).filter(
                        Track.track_genre == cg
                    ).order_by(Track.year.desc()).limit(50).first()
                    if contrast_track:
                        ctid = contrast_track.track_id or f"track_{contrast_track.id}"
                        if not any(r.get("track_id") == ctid for r in results):
                            results.append({
                                "track_id": ctid,
                                "artist_name": contrast_track.artist_name,
                                "track_name": contrast_track.track_name,
                                "track_genre": contrast_track.track_genre,
                                "popularity": contrast_track.popularity,
                                "duration_ms": contrast_track.duration_ms,
                                "danceability": contrast_track.danceability,
                                "energy": contrast_track.energy,
                                "valence": contrast_track.valence,
                                "tempo": contrast_track.tempo,
                                "loudness": contrast_track.loudness,
                                "key": contrast_track.key,
                                "mode": contrast_track.mode,
                                "speechiness": contrast_track.speechiness,
                                "acousticness": contrast_track.acousticness,
                                "instrumentalness": contrast_track.instrumentalness,
                                "liveness": contrast_track.liveness,
                                "time_signature": contrast_track.time_signature,
                                "similarity_score": 0.3,
                                "combined_score": 0.5,
                                "has_lyrics": ctid in lyrics_count,
                                "selected": True,
                                "ref_role": "contrast",
                                "ref_weight": 0.30,
                            })
                        break

            results.sort(key=lambda x: (
                0 if x.get("ref_role") == "primary" else 1 if x.get("ref_role") == "contrast" else 2,
                -x.get("combined_score", 0)
            ))
            results = results[:limit + 2]

            selected_count = 0
            max_selected = 10
            for r in results:
                if r.get("selected"):
                    if selected_count >= max_selected:
                        r["selected"] = False
                    else:
                        selected_count += 1
                elif selected_count < max_selected:
                    r["selected"] = True
                    selected_count += 1

            surprise_element = None
            if genre and genre in SURPRISE_ELEMENTS:
                import random
                surprise_element = random.choice(SURPRISE_ELEMENTS[genre])

            return results, surprise_element
        finally:
            db.close()

    def get_reference_package(self, genre: Optional[str], mood: Optional[str], features: Optional[dict] = None) -> dict:
        profile = self.get_hit_profile(genre) if genre else None

        similar = []
        if features or profile:
            query_features = features or {}
            if profile and not query_features:
                query_features = {
                    "danceability": profile["avg_danceability"],
                    "energy": profile["avg_energy"],
                    "valence": profile["avg_valence"],
                    "tempo": profile["avg_tempo"],
                    "loudness": profile["avg_loudness"],
                    "speechiness": profile["avg_speechiness"],
                    "acousticness": profile["avg_acousticness"],
                    "instrumentalness": profile["avg_instrumentalness"],
                    "liveness": profile["avg_liveness"],
                }
            similar = self.get_similar_tracks(query_features, genre=genre, limit=5)

        lyrics_samples = self.get_lyrics_by_genre(genre, limit=3) if genre else []

        return {"profile": profile, "similar_tracks": similar, "lyrics_samples": lyrics_samples}

    def get_reference_package_from_search(self, ref_result: dict, genre: Optional[str], mood: Optional[str], features: Optional[dict] = None) -> dict:
        ref_features = ref_result.get("features")
        if ref_features:
            query_features = ref_features
        else:
            query_features = features

        resolved_genre = ref_result.get("genre_resolved") or genre
        profile = self.get_hit_profile(resolved_genre) if resolved_genre else None

        similar = []
        if query_features:
            similar = self.get_similar_tracks(query_features, genre=resolved_genre, limit=5)

        artist_tracks = ref_result.get("artist_tracks", [])
        if artist_tracks and len(similar) < 5:
            existing_ids = {s.get("track_id") for s in similar}
            for at in artist_tracks:
                if at.get("track_id") not in existing_ids:
                    at["similarity_score"] = 0.8
                    similar.append(at)
                    if len(similar) >= 5:
                        break

        lyrics_samples = []
        if similar:
            lyrics_samples = self.get_lyrics_by_tracks(similar, limit=3)
        if not lyrics_samples and resolved_genre:
            lyrics_samples = self.get_lyrics_by_genre(resolved_genre, limit=3)

        return {
            "profile": profile,
            "similar_tracks": similar,
            "lyrics_samples": lyrics_samples,
            "ref_result": ref_result,
        }

    def get_genre_list(self) -> list[str]:
        db = SessionLocal()
        try:
            result = db.query(Track.track_genre).distinct().filter(Track.track_genre.isnot(None)).all()
            return sorted([r[0] for r in result if r[0]])
        finally:
            db.close()

    def get_stats(self) -> dict:
        db = SessionLocal()
        try:
            return {
                "total_tracks": db.query(Track).count(),
                "popular_tracks": db.query(Track).filter(Track.is_popular == True).count(),
                "total_lyrics": db.query(Lyrics).count(),
                "hit_profiles": db.query(HitProfile).count(),
                "genres": db.query(Track.track_genre).distinct().filter(Track.track_genre.isnot(None)).count(),
            }
        finally:
            db.close()

    @staticmethod
    def derive_mood(avg_features: dict) -> str:
        if not avg_features:
            return "neutral"
        target_vec = np.array([
            avg_features.get("danceability", 0.5),
            avg_features.get("energy", 0.5),
            avg_features.get("valence", 0.5),
            (avg_features.get("tempo", 120)) / 200.0,
            abs(avg_features.get("loudness", -8)) / 60.0,
            avg_features.get("speechiness", 0.05),
            avg_features.get("acousticness", 0.1),
            avg_features.get("instrumentalness", 0.0),
            avg_features.get("liveness", 0.1),
        ])
        best_mood = "neutral"
        best_dist = float("inf")
        for mood_name, mood_vals in MOOD_PRESETS.items():
            mood_vec = np.array([
                mood_vals.get("danceability", 0.5),
                mood_vals.get("energy", 0.5),
                mood_vals.get("valence", 0.5),
                mood_vals.get("tempo", 120) / 200.0,
                abs(mood_vals.get("loudness", -8)) / 60.0,
                mood_vals.get("speechiness", 0.05),
                mood_vals.get("acousticness", 0.1),
                mood_vals.get("instrumentalness", 0.0),
                mood_vals.get("liveness", 0.1),
            ])
            dist = float(np.linalg.norm(mood_vec - target_vec))
            if dist < best_dist:
                best_dist = dist
                best_mood = mood_name
        return best_mood

    def search_artists(self, query: str, language: Optional[str] = None, limit: int = 10) -> list[dict]:
        db = SessionLocal()
        try:
            q = f"%{query.strip()}%"
            if language:
                rows = db.query(
                    Track.artist_name,
                    func.count(Track.id).label("track_count"),
                ).filter(
                    Track.artist_name.ilike(q),
                    Track.track_id.in_(
                        db.query(Lyrics.track_id).filter(Lyrics.language == language)
                    ),
                ).group_by(Track.artist_name).order_by(func.count(Track.id).desc()).limit(limit).all()

                results = []
                for name, tc in rows:
                    lc = db.query(func.count()).filter(
                        Lyrics.artist_name.ilike(f"%{name}%"),
                        Lyrics.language == language,
                    ).first()[0]
                    genre_rows = db.query(
                        Track.track_genre,
                        func.count(Track.id).label("cnt"),
                    ).filter(
                        Track.artist_name.ilike(f"%{name}%"),
                        Track.track_id.in_(db.query(Lyrics.track_id).filter(Lyrics.language == language)),
                        Track.track_genre != None,
                    ).group_by(Track.track_genre).order_by(func.count(Track.id).desc()).limit(5).all()
                    top_genres = [{"genre": r[0], "count": r[1]} for r in genre_rows if r[0]]
                    genres = [r["genre"] for r in top_genres]
                    results.append({"name": name, "track_count": tc, "lyrics_count": lc, "genres": genres, "top_genres": top_genres})
                return results
            else:
                rows = db.query(
                    Track.artist_name,
                    func.count(Track.id).label("track_count"),
                ).filter(
                    Track.artist_name.ilike(q),
                ).group_by(Track.artist_name).order_by(func.count(Track.id).desc()).limit(limit).all()

                results = []
                for name, tc in rows:
                    genre_rows = db.query(
                        Track.track_genre,
                        func.count(Track.id).label("cnt"),
                    ).filter(
                        Track.artist_name.ilike(f"%{name}%"),
                        Track.track_genre != None,
                    ).group_by(Track.track_genre).order_by(func.count(Track.id).desc()).limit(5).all()
                    top_genres = [{"genre": r[0], "count": r[1]} for r in genre_rows if r[0]]
                    genres = [r["genre"] for r in top_genres]
                    lc = db.query(func.count()).filter(
                        Lyrics.artist_name.ilike(f"%{name}%"),
                    ).first()[0]
                    results.append({"name": name, "track_count": tc, "lyrics_count": lc, "genres": genres, "top_genres": top_genres})
                return results
        finally:
            db.close()

    def get_artist_stats(self, artist_name: str, language: Optional[str] = None) -> dict:
        db = SessionLocal()
        try:
            clean = artist_name.split(",")[0].split(";")[0].strip()
            if language:
                track_ids_sub = db.query(Lyrics.track_id).filter(Lyrics.language == language).subquery()
                query = db.query(Track).filter(
                    Track.artist_name.ilike(f"%{clean}%"),
                    Track.track_id.in_(db.query(Lyrics.track_id).filter(Lyrics.language == language)),
                )
            else:
                query = db.query(Track).filter(Track.artist_name.ilike(f"%{clean}%"))

            tracks = query.all()
            if not tracks:
                return {"artist_name": clean, "track_count": 0, "lyrics_count": 0, "avg_bpm": 120.0,
                        "dominant_key": None, "dominant_mode": None, "avg_duration_ms": 0,
                        "derived_mood": "", "dominant_genre": "", "avg_features": {}}

            avg_features = {}
            for k in FEATURE_KEYS:
                vals = [getattr(t, k) for t in tracks if getattr(t, k) is not None]
                avg_features[k] = float(np.mean(vals)) if vals else 0.5

            avg_bpm = avg_features.get("tempo", 120.0)
            key_counts = {}
            for t in tracks:
                if t.key is not None:
                    key_counts[t.key] = key_counts.get(t.key, 0) + 1
            dominant_key = max(key_counts, key=key_counts.get) if key_counts else None

            mode_counts = {}
            for t in tracks:
                if t.mode is not None:
                    mode_counts[t.mode] = mode_counts.get(t.mode, 0) + 1
            dominant_mode = max(mode_counts, key=mode_counts.get) if mode_counts else None

            durations = [t.duration_ms for t in tracks if t.duration_ms]
            avg_duration_ms = float(np.mean(durations)) if durations else 0.0

            genre_counts = {}
            for t in tracks:
                g = t.track_genre
                if g:
                    genre_counts[g] = genre_counts.get(g, 0) + 1
            sorted_genres = sorted(genre_counts.items(), key=lambda x: -x[1])
            top_genres = [{"genre": g, "count": c} for g, c in sorted_genres[:5]]
            dominant_genre = sorted_genres[0][0] if sorted_genres else ""

            if language:
                lyrics_count = db.query(func.count()).filter(
                    Lyrics.artist_name.ilike(f"%{clean}%"),
                    Lyrics.language == language,
                ).first()[0]
            else:
                lyrics_count = db.query(func.count()).filter(
                    Lyrics.artist_name.ilike(f"%{clean}%"),
                ).first()[0]

            derived_mood = self.derive_mood(avg_features)

            return {
                "artist_name": clean,
                "track_count": len(tracks),
                "lyrics_count": lyrics_count,
                "avg_bpm": round(avg_bpm, 1),
                "dominant_key": dominant_key,
                "dominant_mode": dominant_mode,
                "avg_duration_ms": round(avg_duration_ms),
                "derived_mood": derived_mood,
                "dominant_genre": dominant_genre,
                "top_genres": top_genres,
                "avg_features": {k: round(v, 3) for k, v in avg_features.items()},
            }
        finally:
            db.close()

    def get_tracks_by_artists(self, artist_names: list[str], language: Optional[str] = None, limit: int = 10) -> list[dict]:
        db = SessionLocal()
        try:
            all_tracks = []
            for name in artist_names:
                clean = name.split(",")[0].split(";")[0].strip()
                if language:
                    query = db.query(Track).filter(
                        Track.artist_name.ilike(f"%{clean}%"),
                        Track.track_id.in_(db.query(Lyrics.track_id).filter(Lyrics.language == language)),
                    )
                else:
                    query = db.query(Track).filter(Track.artist_name.ilike(f"%{clean}%"))
                tracks = query.all()
                for t in tracks:
                    all_tracks.append(self._track_to_dict(t))

            all_tracks.sort(key=lambda t: t.get("popularity", 0) or 0, reverse=True)
            return all_tracks[:limit]
        finally:
            db.close()

    def get_artist_reference_package(self, primary_artist: str, secondary_artists: list[str],
                                      language: str, features: Optional[dict] = None,
                                      genre_override: Optional[str] = None) -> dict:
        db = SessionLocal()
        try:
            all_artist_names = [primary_artist] + secondary_artists[:2]
            all_tracks = self.get_tracks_by_artists(all_artist_names, language=language, limit=50)

            primary_tracks = self.get_tracks_by_artists([primary_artist], language=language, limit=30)
            secondary_tracks = []
            for sa in secondary_artists[:2]:
                secondary_tracks.extend(self.get_tracks_by_artists([sa], language=language, limit=15))

            expanded_artists = []
            if len(primary_tracks) < 10:
                primary_stats = self.get_artist_stats(primary_artist, language=language)
                genre = genre_override or primary_stats.get("dominant_genre", "")
                if genre:
                    expand_rows = db.query(
                        Track.artist_name,
                    ).filter(
                        Track.track_genre == genre,
                        Track.track_id.in_(db.query(Lyrics.track_id).filter(Lyrics.language == language)),
                        ~Track.artist_name.ilike(f"%{primary_artist.split(',')[0].strip()}%"),
                    ).group_by(Track.artist_name).order_by(func.count(Track.id).desc()).limit(5).all()

                    for row in expand_rows:
                        exp_name = row[0]
                        if exp_name not in all_artist_names and exp_name not in expanded_artists:
                            expanded_artists.append(exp_name)
                            exp_tracks = self.get_tracks_by_artists([exp_name], language=language, limit=10)
                            primary_tracks.extend(exp_tracks)
                            if len(primary_tracks) >= 20:
                                break

            for pt in primary_tracks:
                pt["ref_role"] = "primary"
                pt["ref_weight"] = 0.60
                pt["selected"] = True

            for st in secondary_tracks:
                st["ref_role"] = "contrast"
                st["ref_weight"] = 0.30
                st["selected"] = True

            all_selected = primary_tracks + secondary_tracks
            existing_ids = {t.get("track_id") for t in all_selected}

            surprise_tracks = []
            top_genres = []
            dominant_genre = genre_override or ""
            if primary_tracks:
                genre_counts = {}
                for t in primary_tracks:
                    g = t.get("track_genre", "")
                    if g:
                        genre_counts[g] = genre_counts.get(g, 0) + 1
                sorted_genres = sorted(genre_counts.items(), key=lambda x: -x[1])
                top_genres = [{"genre": g, "count": c} for g, c in sorted_genres[:5]]
                if not dominant_genre:
                    dominant_genre = sorted_genres[0][0] if sorted_genres else ""

            if dominant_genre and dominant_genre in CROSS_GENRE_MAP:
                for cg in CROSS_GENRE_MAP[dominant_genre]:
                    surprise_row = db.query(Track).filter(
                        Track.track_genre == cg,
                        Track.track_id.in_(db.query(Lyrics.track_id).filter(Lyrics.language == language)),
                        ~Track.track_id.in_(list(existing_ids)),
                    ).order_by(Track.popularity.desc()).limit(10).first() if existing_ids else db.query(Track).filter(
                        Track.track_genre == cg,
                        Track.track_id.in_(db.query(Lyrics.track_id).filter(Lyrics.language == language)),
                    ).order_by(Track.popularity.desc()).limit(10).first()

                    if surprise_row:
                        st_dict = self._track_to_dict(surprise_row)
                        st_dict["ref_role"] = "surprise"
                        st_dict["ref_weight"] = 0.10
                        st_dict["selected"] = True
                        surprise_tracks.append(st_dict)
                        break

            reference_tracks = primary_tracks + secondary_tracks + surprise_tracks

            max_primary = 8
            max_contrast = 5
            max_surprise = 2
            primary_tracks.sort(key=lambda x: -(x.get("popularity") or 0))
            secondary_tracks.sort(key=lambda x: -(x.get("popularity") or 0))
            trimmed_primary = primary_tracks[:max_primary]
            trimmed_contrast = secondary_tracks[:max_contrast]
            trimmed_surprise = surprise_tracks[:max_surprise]
            reference_tracks = trimmed_primary + trimmed_contrast + trimmed_surprise

            # Construir lyrics_samples con ref_role propagado correctamente.
            # Las letras PRIMARY reciben más texto y más slots; contrast y surprise
            # reciben menos para que no diluyan la identidad del artista principal.
            lyrics_samples = []

            def _fetch_lyrics_for_bucket(track_bucket, role, weight, max_slots, max_chars):
                ids = {t.get("track_id") for t in track_bucket if t.get("track_id")}
                if not ids:
                    return []
                rows = db.query(Lyrics).filter(
                    Lyrics.track_id.in_(list(ids)),
                    Lyrics.language == language,
                ).limit(max_slots).all()
                result = []
                for l in rows:
                    if l.lyrics_text:
                        result.append({
                            "track_id": l.track_id,
                            "artist": l.artist_name,
                            "track": l.track_name,
                            "text": l.lyrics_text[:max_chars],
                            "ref_role": role,
                            "ref_weight": weight,
                        })
                return result

            lyrics_samples += _fetch_lyrics_for_bucket(trimmed_primary,  "primary",  0.60, max_slots=3, max_chars=2000)
            lyrics_samples += _fetch_lyrics_for_bucket(trimmed_contrast,  "contrast", 0.30, max_slots=1, max_chars=1000)
            lyrics_samples += _fetch_lyrics_for_bucket(trimmed_surprise,  "surprise", 0.10, max_slots=1, max_chars=500)

            # Fallback: si no se encontraron letras del artista principal,
            # buscar directamente por nombre de artista.
            if not any(l["ref_role"] == "primary" for l in lyrics_samples):
                clean_primary = primary_artist.split(",")[0].strip()
                fallback_rows = db.query(Lyrics).filter(
                    Lyrics.language == language,
                    Lyrics.artist_name.ilike(f"%{clean_primary}%"),
                ).limit(3).all()
                for l in fallback_rows:
                    if l.lyrics_text:
                        lyrics_samples.insert(0, {
                            "track_id": l.track_id,
                            "artist": l.artist_name,
                            "track": l.track_name,
                            "text": l.lyrics_text[:2000],
                            "ref_role": "primary",
                            "ref_weight": 0.60,
                        })

            combined_features = {}
            if all_selected:
                for k in FEATURE_KEYS:
                    vals = [t.get(k) for t in all_selected if t.get(k) is not None]
                    combined_features[k] = float(np.mean(vals)) if vals else 0.5
            elif features:
                combined_features = features

            bpm = round(combined_features.get("tempo", 120.0))
            key_vals = [t.get("key") for t in all_selected if t.get("key") is not None]
            dominant_key = int(np.round(np.mean(key_vals))) if key_vals else 0
            mode_vals = [t.get("mode") for t in all_selected if t.get("mode") is not None]
            dominant_mode = int(np.round(np.mean(mode_vals))) if mode_vals else 0
            durations = [t.get("duration_ms") for t in all_selected if t.get("duration_ms")]
            avg_duration_ms = round(float(np.mean(durations))) if durations else 180000
            derived_mood = self.derive_mood(combined_features)

            KEY_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
            key_name = KEY_NAMES[dominant_key % 12] if dominant_key is not None else "C"
            mode_name = "major" if dominant_mode == 1 else "minor"
            key_scale = f"{key_name} {mode_name}"

            auto_params = {
            "bpm": bpm,
            "key_scale": key_scale,
            "key": dominant_key,
            "mode": dominant_mode,
            "avg_duration_ms": avg_duration_ms,
            "derived_mood": derived_mood,
            "dominant_genre": dominant_genre,
            "top_genres": top_genres,
            "avg_features": {k: round(v, 3) for k, v in combined_features.items()},
            }

            selected_count = 0
            max_selected = 10
            for r in reference_tracks:
                if r.get("selected"):
                    if selected_count >= max_selected:
                        r["selected"] = False
                    else:
                        selected_count += 1

            surprise_element = None
            if dominant_genre and dominant_genre in SURPRISE_ELEMENTS:
                import random
                surprise_element = random.choice(SURPRISE_ELEMENTS[dominant_genre])

            profile = self.get_hit_profile(dominant_genre) if dominant_genre else None

            return {
                "auto_params": auto_params,
                "reference_tracks": reference_tracks,
                "lyrics_samples": lyrics_samples,
                "expanded_artists": expanded_artists,
                "profile": profile,
                "surprise_element": surprise_element,
            }
        finally:
            db.close()
