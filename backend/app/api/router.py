import json
import logging
import re
import time
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.services.registry import lm_studio, ace_step, knowledge_base, hit_predictor
from backend.app.models.tables import GeneratedTrack
from backend.app.schemas.schemas import (
    GenerateRequest, GenerateResponse, HitPredictionRequest, HitPredictionResponse,
    TrackSearchRequest, TrackSchema, HitProfileSchema, PipelineTrace, ReferenceTrack,
    LyricSample, FullSearchRequest, FullSearchResponse,
    OptimizePromptRequest, OptimizePromptResponse, ReferenceTrackWithSelection,
    ComposeLyricsRequest, ComposeLyricsResponse,
    ModelProfileSchema, ModelProfileUpdateRequest,
    ArtistSearchResult, ArtistStats, OptimizePromptArtistRequest,
)
from backend.app.services.knowledge_base import MOOD_PRESETS
from backend.app.services.pipeline_logger import start_session, append_step, update_step, get_step_data

router = APIRouter()
logger = logging.getLogger("spotigem")


def _prompt_features(prompt: str, mood: Optional[str] = None) -> dict:
    p = prompt.lower()
    base = {"danceability": 0.6, "energy": 0.6, "valence": 0.5, "tempo": 120,
            "loudness": -8, "speechiness": 0.05, "acousticness": 0.3,
            "instrumentalness": 0.0, "liveness": 0.1}

    if mood and mood in MOOD_PRESETS:
        base.update(MOOD_PRESETS[mood])
    elif mood == "happy":
        base.update({"danceability": 0.7, "energy": 0.8, "valence": 0.8})
    elif mood == "sad":
        base.update({"danceability": 0.4, "energy": 0.3, "valence": 0.2})
    elif mood == "energetic":
        base.update({"danceability": 0.8, "energy": 0.9, "valence": 0.6, "tempo": 140})
    elif mood == "dark":
        base.update({"danceability": 0.5, "energy": 0.7, "valence": 0.2, "loudness": -12})

    if not any(w in p for w in ["bpm", "tempo"]):
        if any(w in p for w in ["fast", "accelerate", "supersonic", "speed", "rush", "chaotic", "intense"]):
            base["tempo"] = max(base.get("tempo", 120), 150)
        elif any(w in p for w in ["slow", "ballad", "dreamy", "chill", "laid"]):
            base["tempo"] = min(base.get("tempo", 120), 80)
        elif any(w in p for w in ["mid", "groove", "funky"]):
            base["tempo"] = 105

    if any(w in p for w in ["bass", "808", "heavy", "distort", "aggressive", "hard"]):
        base["energy"] = min(1.0, base["energy"] + 0.2)
        base["loudness"] = max(-12, base.get("loudness", -8) - 2)
    if any(w in p for w in ["acoustic", "piano", "soft", "gentle", "calm"]):
        base["acousticness"] = min(1.0, base["acousticness"] + 0.3)
        base["energy"] = max(0.1, base["energy"] - 0.2)
    if any(w in p for w in ["vocal", "sing", "rap", "hip", "hook", "lyric"]):
        base["instrumentalness"] = max(0.0, base["instrumentalness"] - 0.1)
        base["speechiness"] = min(1.0, base["speechiness"] + 0.1)
    if any(w in p for w in ["dance", "club", "groove", "rhythm", "beat"]):
        base["danceability"] = min(1.0, base["danceability"] + 0.15)
    if any(w in p for w in ["sad", "melancholic", "dark", "moody", "brooding"]):
        base["valence"] = max(0.0, base["valence"] - 0.2)
    elif any(w in p for w in ["happy", "bright", "cheerful", "uplift", "joy"]):
        base["valence"] = min(1.0, base["valence"] + 0.2)
    return base


@router.get("/status")
async def get_status():
    lm_available = await lm_studio.check_availability()
    ace_ok = await ace_step.check_available()
    active_profile = lm_studio.get_active_profile()
    return {
        "lm_studio": {"available": lm_available, "models": await lm_studio.get_loaded_models() if lm_available else [],
                       "active_model": lm_studio._model_id,
                       "active_profile": {"family": active_profile.family, "json_reliability": active_profile.json_reliability} if active_profile else None},
        "ace_step": {"loaded": ace_ok, "api_url": ace_step.ace_api_url},
        "knowledge_base": {"ready": knowledge_base.is_ready(), "stats": knowledge_base.get_stats() if knowledge_base.is_ready() else {}},
    }


@router.get("/tracks/{track_id}")
async def get_track(track_id: int, db: Session = Depends(get_db)):
    record = db.query(GeneratedTrack).filter(GeneratedTrack.id == track_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Track not found")
    return {
        "id": record.id,
        "audio_path": record.audio_path or "pending",
        "prompt": record.prompt,
        "genre": record.genre,
        "hit_prediction_score": record.hit_prediction_score or 0.0,
        "hit_prediction_label": record.hit_prediction_label,
        "pipeline_trace": json.loads(record.pipeline_trace) if record.pipeline_trace else None,
        "created_at": str(record.created_at) if record.created_at else None,
    }


@router.post("/generate", response_model=GenerateResponse)
async def generate_track(req: GenerateRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    gen_record = GeneratedTrack(prompt=req.optimized_prompt or req.prompt, genre=req.genre, mood=req.mood, lyrics=req.lyrics)
    db.add(gen_record)
    db.commit()
    db.refresh(gen_record)

    gen_trace = {
        "trace_id": f"gen_{gen_record.id}_{int(time.time())}",
        "step": "generate",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "record_id": gen_record.id,
        "original_prompt": req.prompt,
        "optimized_prompt": req.optimized_prompt,
        "final_prompt": req.optimized_prompt or req.prompt,
        "genre": req.genre, "mood": req.mood,
        "lyrics_provided": bool(req.lyrics),
        "lyrics_full": req.lyrics or "",
        "voice_type": req.voice_type, "lyrics_language": req.lyrics_language,
        "bpm": req.bpm, "key_scale": req.key_scale, "time_signature": req.time_signature,
        "song_structure": req.song_structure, "duration_seconds": req.duration_seconds,
    }
    try:
        append_step(req.session_id, "generate_input", gen_trace)
        logger.info(f"Generate trace appended to session: {req.session_id}")
    except Exception as e:
        logger.warning(f"Failed to append generate trace: {e}")

    background_tasks.add_task(_generate_audio_pipeline, gen_record.id, req)
    return GenerateResponse(id=gen_record.id, audio_path="pending", prompt=req.optimized_prompt or req.prompt, genre=req.genre, hit_prediction_score=0.0, message="Generation queued")


async def _generate_audio_pipeline(record_id: int, req: GenerateRequest):
    from backend.app.core.database import SessionLocal
    db = SessionLocal()
    try:
        record = db.query(GeneratedTrack).filter(GeneratedTrack.id == record_id).first()
        if not record:
            return

        final_prompt = req.optimized_prompt or req.prompt
        bpm = req.bpm or 120
        key_scale = req.key_scale or "C major"
        time_sig = req.time_signature or "4/4"
        song_structure = req.song_structure or ""

        voice = req.validated_voice_type()
        lang = req.validated_lyrics_language()

        audio_duration = req.duration_seconds or 30.0
        similar = []
        prompt_features = _prompt_features(req.prompt, req.mood)
        ref_package = {}

        if not req.duration_seconds:
            ref_result = knowledge_base.search_by_reference(req.prompt)
            if ref_result.get("found") and ref_result.get("features"):
                ref_package = knowledge_base.get_reference_package_from_search(
                    ref_result=ref_result, genre=ref_result.get("genre_resolved") or req.genre,
                    mood=req.mood, features=prompt_features,
                )
            else:
                ref_package = knowledge_base.get_reference_package(
                    genre=req.genre, mood=req.mood, features=prompt_features,
                )
            similar = ref_package.get("similar_tracks", [])
            if similar:
                durations = [t.get("duration_ms") for t in similar if t.get("duration_ms")]
                if durations:
                    avg_ms = sum(durations) / len(durations)
                    audio_duration = max(15.0, min(300.0, avg_ms / 1000.0))

        vocal_language = lang or "en"
        if voice == "instrumental":
            lyrics_for_ace = None
        else:
            lyrics_for_ace = _clean_lyrics_for_ace(req.lyrics) if req.lyrics else None

        try:
            audio_path = await ace_step.generate(
                prompt=final_prompt, lyrics=lyrics_for_ace,
                audio_duration=audio_duration, record_id=record.id,
                bpm=bpm, key_scale=key_scale, time_signature=time_sig,
                vocal_language=vocal_language,
            )
            record.audio_path = audio_path
            try:
                update_step(req.session_id, "generate_result", {"audio_path": audio_path, "status": "audio_generated"})
            except Exception:
                pass
        except Exception as e:
            record.hit_prediction_label = f"ace_error: {e}"
            try:
                update_step(req.session_id, "generate_result", {"status": "ace_error", "error": str(e)})
            except Exception:
                pass
            db.commit()
            db.close()
            return

        features_for_prediction = prompt_features
        if ref_package.get("profile"):
            p = ref_package["profile"]
            features_for_prediction = {
                "danceability": p.get("avg_danceability", 0.6), "energy": p.get("avg_energy", 0.6),
                "valence": p.get("avg_valence", 0.5), "tempo": float(bpm),
                "loudness": p.get("avg_loudness", -8), "speechiness": p.get("avg_speechiness", 0.05),
                "acousticness": p.get("avg_acousticness", 0.3), "instrumentalness": p.get("avg_instrumentalness", 0.0),
                "liveness": p.get("avg_liveness", 0.1),
            }

        prediction = hit_predictor.predict(features_for_prediction, genre=req.genre)
        record.hit_prediction_score = prediction["hit_score"]
        record.hit_prediction_label = prediction["hit_label"]
        comparison = hit_predictor.compare_with_reference(features_for_prediction, similar)

        try:
            update_step(req.session_id, "generate_result", {
                "hit_score": prediction["hit_score"],
                "hit_label": prediction["hit_label"],
                "comparison": comparison,
            })
        except Exception:
            pass

        trace_similar = []
        for t in similar[:5]:
            trace_similar.append(ReferenceTrack(
                track_name=t.get("track_name", "?"), artist_name=t.get("artist_name", "?"),
                similarity_score=t.get("similarity_score", 0),
                danceability=t.get("danceability", 0), energy=t.get("energy", 0),
                valence=t.get("valence", 0), tempo=t.get("tempo", 0),
                key=t.get("key"), mode=t.get("mode"),
                speechiness=t.get("speechiness"), acousticness=t.get("acousticness"),
                instrumentalness=t.get("instrumentalness"), time_signature=t.get("time_signature"),
            ))

        trace = PipelineTrace(
            reference_tracks=trace_similar, lyrics_samples=[],
            hit_profile_used=ref_package.get("profile"),
            lm_prompt=final_prompt, lyrics_full=req.lyrics or "",
            lm_params={"bpm": bpm, "key_scale": key_scale, "time_signature": time_sig, "song_structure": song_structure},
            comparison=comparison,
        )
        record.pipeline_trace = json.dumps(trace.model_dump())
        record.ace_params = json.dumps({"bpm": bpm, "key_scale": key_scale, "time_signature": time_sig, "song_structure": song_structure})
        db.commit()

    except Exception as e:
        try:
            record = db.query(GeneratedTrack).filter(GeneratedTrack.id == record_id).first()
            if record:
                record.hit_prediction_label = f"pipeline_error: {e}"
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


def _track_summary(t):
    return {"track_id": t.get("track_id"), "track_name": t.get("track_name"), "artist_name": t.get("artist_name"),
            "track_genre": t.get("track_genre"), "ref_role": t.get("ref_role"), "ref_weight": t.get("ref_weight"),
            "selected": t.get("selected", False)}


def _ref_track_to_response(t, surprise_element):
    return ReferenceTrackWithSelection(
        track_id=t.get("track_id", ""), track_name=t.get("track_name", "?"),
        artist_name=t.get("artist_name", "?"), track_genre=t.get("track_genre"),
        popularity=t.get("popularity", 0), duration_ms=t.get("duration_ms"),
        danceability=t.get("danceability", 0.5), energy=t.get("energy", 0.5),
        valence=t.get("valence", 0.5), tempo=t.get("tempo", 120),
        loudness=t.get("loudness"), key=t.get("key"), mode=t.get("mode"),
        speechiness=t.get("speechiness"), acousticness=t.get("acousticness"),
        instrumentalness=t.get("instrumentalness"), liveness=t.get("liveness"),
        time_signature=t.get("time_signature"), similarity_score=t.get("similarity_score", 0),
        combined_score=t.get("combined_score", 0), has_lyrics=t.get("has_lyrics", False),
        selected=t.get("selected", False), ref_role=t.get("ref_role", "primary"),
        ref_weight=t.get("ref_weight", 0.60),
        surprise_element=surprise_element if t.get("ref_role") == "surprise" else None,
    )


_PRODUCTION_RE = re.compile(
    r"(?i)(fingerpick|steel guitar|vinyl|crackle|close-?mic|reverb|key change|vocal|fade[sd]?"
    r"|whisper|drum|snare|slide|orchestr|instrument|bar[s]?\b|music|backing"
    r"|harmon(?:y|ies)|pad[s]?|mix|pan|compress|limit|eq|filter|delay|chorus\s+eff)"
)


def _clean_lyrics_for_ace(lyrics: str) -> str:
    cleaned = []
    for line in lyrics.split("\n"):
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            cleaned.append(line)
            continue
        if stripped and _PRODUCTION_RE.search(stripped):
            continue
        cleaned.append(line)
    result = "\n".join(cleaned).strip()
    return result if result else lyrics


@router.post("/optimize-prompt", response_model=OptimizePromptResponse)
async def optimize_prompt(req: OptimizePromptRequest):
    session_id = f"sess_{int(time.time())}"
    start_session(session_id)
    append_step(session_id, "optimize_input", {"mode": "custom", "original_prompt": req.prompt, "genre": req.genre, "mood": req.mood})

    ref_result = knowledge_base.search_by_reference(req.prompt)
    prompt_features = _prompt_features(req.prompt, req.mood)

    genre = req.genre
    if ref_result.get("found") and ref_result.get("genre_resolved"):
        genre = ref_result.get("genre_resolved") or genre

    hit_profile = None
    if genre:
        hit_profile = knowledge_base.get_hit_profile(genre)

    artist_tracks = ref_result.get("artist_tracks", []) if ref_result.get("found") else []
    artist_subgenres = ref_result.get("artist_subgenres", [])

    reference_tracks, surprise_element = knowledge_base.get_reference_tracks(
        features=ref_result.get("features") or prompt_features,
        genre=genre, artist_tracks=artist_tracks, artist_subgenres=artist_subgenres, limit=10,
    )
    append_step(session_id, "kb_tracks", {"tracks": [_track_summary(t) for t in reference_tracks], "surprise_element": surprise_element})

    available_moods = list(MOOD_PRESETS.keys())

    lm_result = await lm_studio.optimize_prompt(
        reference_tracks=reference_tracks, user_prompt=req.prompt, genre=genre,
        mood=req.mood, voice_type=req.validated_voice_type(),
        hit_profile=hit_profile, available_moods=available_moods, surprise_element=surprise_element,
    )
    append_step(session_id, "lm_optimize", {
        "raw_response": lm_result.get("_lm_raw_response", ""),
        "parsed_response": lm_result.get("_lm_parsed_response", {}),
        "success": lm_result.get("_lm_success", False),
        "optimized_prompt": lm_result.get("prompt", req.prompt),
        "bpm": lm_result.get("bpm", 120), "key_scale": lm_result.get("key_scale", "C major"),
        "time_signature": lm_result.get("time_signature", "4/4"),
    })

    ref_tracks_response = [_ref_track_to_response(t, surprise_element) for t in reference_tracks]

    result = OptimizePromptResponse(
        session_id=session_id,
        original_prompt=req.prompt, optimized_prompt=lm_result.get("prompt", req.prompt),
        bpm=lm_result.get("bpm", 120), key_scale=lm_result.get("key_scale", "C major"),
        time_signature=lm_result.get("time_signature", "4/4"),
        song_structure=lm_result.get("song_structure", ""), mood=lm_result.get("mood", req.mood or ""),
        reference_tracks=ref_tracks_response,
        ref_found=ref_result.get("found", False), ref_type=ref_result.get("ref_type"), ref_name=ref_result.get("ref_name"),
    )
    logger.info(f"Optimize session: {session_id}")
    return result


@router.post("/optimize-prompt-artist", response_model=OptimizePromptResponse)
async def optimize_prompt_artist(req: OptimizePromptArtistRequest):
    session_id = f"sess_{int(time.time())}"
    start_session(session_id)
    append_step(session_id, "optimize_input", {"mode": "artist", "primary_artist": req.primary_artist,
        "secondary_artists": req.secondary_artists, "language": req.language,
        "genre_override": req.genre_override, "custom_prompt": req.custom_prompt})

    pkg = knowledge_base.get_artist_reference_package(
        primary_artist=req.primary_artist, secondary_artists=req.secondary_artists,
        language=req.language, features=None, genre_override=req.genre_override,
    )
    auto_params = pkg.get("auto_params", {})
    reference_tracks = pkg.get("reference_tracks", [])
    surprise_element = pkg.get("surprise_element")
    profile = pkg.get("profile")
    expanded_artists = pkg.get("expanded_artists", [])
    derived_mood = auto_params.get("derived_mood", "")
    dominant_genre = auto_params.get("dominant_genre", "")

    append_step(session_id, "kb_tracks", {"auto_params": auto_params, "expanded_artists": expanded_artists,
        "tracks": [_track_summary(t) for t in reference_tracks], "surprise_element": surprise_element})

    user_prompt = req.custom_prompt or f"estilo {req.primary_artist}"
    if req.secondary_artists:
        user_prompt += " + " + " + ".join(req.secondary_artists[:2])

    available_moods = list(MOOD_PRESETS.keys())

    lm_result = await lm_studio.optimize_prompt(
        reference_tracks=reference_tracks, user_prompt=user_prompt, genre=dominant_genre,
        mood=derived_mood, voice_type=req.validated_voice_type(), hit_profile=profile,
        available_moods=available_moods, surprise_element=surprise_element,
    )
    append_step(session_id, "lm_optimize", {
        "raw_response": lm_result.get("_lm_raw_response", ""),
        "parsed_response": lm_result.get("_lm_parsed_response", {}),
        "success": lm_result.get("_lm_success", False),
        "optimized_prompt": lm_result.get("prompt", user_prompt),
        "bpm": lm_result.get("bpm", auto_params.get("bpm", 120)),
        "key_scale": lm_result.get("key_scale", auto_params.get("key_scale", "C major")),
        "time_signature": lm_result.get("time_signature", "4/4"),
    })

    ref_tracks_response = [_ref_track_to_response(t, surprise_element) for t in reference_tracks]
    bpm = lm_result.get("bpm", auto_params.get("bpm", 120))
    key_scale = lm_result.get("key_scale", auto_params.get("key_scale", "C major"))
    time_sig = lm_result.get("time_signature", "4/4")

    result = OptimizePromptResponse(
        session_id=session_id,
        original_prompt=user_prompt, optimized_prompt=lm_result.get("prompt", user_prompt),
        bpm=bpm, key_scale=key_scale, time_signature=time_sig,
        song_structure=lm_result.get("song_structure", ""), mood=lm_result.get("mood", derived_mood),
        reference_tracks=ref_tracks_response, ref_found=True, ref_type="artist",
        ref_name=req.primary_artist, auto_params=auto_params, expanded_artists=expanded_artists,
    )
    logger.info(f"Optimize-artist session: {session_id}")
    return result


@router.post("/compose-lyrics", response_model=ComposeLyricsResponse)
async def compose_lyrics(req: ComposeLyricsRequest):
    session_id = req.session_id or f"sess_{int(time.time())}"
    if session_id and not session_id.startswith("sess_"):
        session_id = f"sess_{session_id}"

    if not lm_studio.is_available():
        raise HTTPException(status_code=503, detail="LM Studio not available")

    genre = req.genre
    selected_tracks = []
    for tid in req.selected_track_ids:
        track = knowledge_base.get_track_by_id(tid)
        if track:
            selected_tracks.append(track)

    if not selected_tracks:
        db_tracks = knowledge_base.search_tracks(genre=genre, limit=len(req.selected_track_ids))
        selected_tracks = db_tracks[:len(req.selected_track_ids)]

    kb_step = get_step_data(session_id, "kb_tracks")
    kb_roles = {}
    if kb_step and kb_step.get("tracks"):
        for t in kb_step["tracks"]:
            kb_roles[t.get("track_id")] = {"ref_role": t.get("ref_role", "primary"), "ref_weight": t.get("ref_weight", 0.60)}

    for t in selected_tracks:
        tid = t.get("track_id", "")
        if tid in kb_roles:
            t["ref_role"] = kb_roles[tid]["ref_role"]
            t["ref_weight"] = kb_roles[tid]["ref_weight"]

    append_step(session_id, "user_track_selection", {
        "selected_track_ids": req.selected_track_ids,
        "tracks": [_track_summary(t) for t in selected_tracks],
        "genre": genre, "mood": req.mood, "voice_type": req.voice_type, "lyrics_language": req.lyrics_language,
    })

    if not genre and selected_tracks:
        track_genres = [t.get("track_genre", "") for t in selected_tracks if t.get("track_genre")]
        if track_genres:
            from collections import Counter
            genre = Counter(track_genres).most_common(1)[0][0]

    reference_lyrics = knowledge_base.get_lyrics_by_tracks(selected_tracks, limit=5)

    track_role_map = {
        t.get("track_id"): {
            "ref_role": t.get("ref_role", "primary"),
            "ref_weight": t.get("ref_weight", 0.60),
        }
        for t in selected_tracks
    }

    for lyric in reference_lyrics:
        tid = lyric.get("track_id", "")
        role_info = track_role_map.get(tid, {"ref_role": "primary", "ref_weight": 0.60})
        lyric["ref_role"] = role_info["ref_role"]
        lyric["ref_weight"] = role_info["ref_weight"]

    primary_lyrics = [l for l in reference_lyrics if l.get("ref_role") == "primary"]
    logger.info(f"Primary lyrics for fingerprint: {[l.get('track') for l in primary_lyrics]}")
    artist_fingerprint = ""
    if primary_lyrics:
        try:
            artist_fingerprint = await lm_studio.analyze_artist_voice(primary_lyrics)
        except Exception as e:
            logger.warning(f"analyze_artist_voice failed (non-fatal): {e}")

    try:
        compose_result = await lm_studio.compose_lyrics(
            prompt=req.prompt, reference_lyrics=reference_lyrics,
            voice_type=req.validated_voice_type(), backing_vocals=req.validated_backing_vocals(),
            lyrics_language=req.validated_lyrics_language(), genre=genre, mood=req.mood,
            artist_fingerprint=artist_fingerprint,
        )
        lyrics = compose_result["lyrics"] if isinstance(compose_result, dict) else compose_result
        compose_raw = compose_result.get("_lm_raw_response", "") if isinstance(compose_result, dict) else ""

        append_step(session_id, "lm_compose", {
            "raw_response": compose_raw, "composed_lyrics": lyrics,
            "reference_lyrics_sources": [{"track_id": l.get("track_id"), "artist": l.get("artist"),
                "track": l.get("track"), "ref_role": l.get("ref_role"), "ref_weight": l.get("ref_weight"),
                "lyrics_excerpt": (l.get("text", "") or "")[:500]} for l in reference_lyrics],
            "artist_fingerprint": artist_fingerprint,
        })

        return ComposeLyricsResponse(session_id=session_id, lyrics=lyrics, reference_count=len(reference_lyrics))
    except Exception as e:
        append_step(session_id, "lm_compose_error", {"error": str(e)})
        raise HTTPException(status_code=500, detail=f"Lyrics composition failed: {e}")


@router.post("/predict-hit", response_model=HitPredictionResponse)
async def predict_hit(req: HitPredictionRequest):
    audio_features = {k: getattr(req, k) for k in ["danceability", "energy", "valence", "tempo", "loudness", "speechiness", "acousticness", "instrumentalness", "liveness"]}
    result = hit_predictor.predict(audio_features, genre=req.genre)
    if lm_studio.is_available():
        try:
            ai_analysis = await lm_studio.analyze_hit_potential(
                prompt=f"Genre: {req.genre or 'pop'}, features: {audio_features}",
                audio_features=audio_features,
            )
            result["ai_analysis"] = ai_analysis
        except Exception:
            pass
    return HitPredictionResponse(**{k: v for k, v in result.items() if k in HitPredictionResponse.model_fields})


@router.post("/search-tracks", response_model=list[TrackSchema])
async def search_tracks(req: TrackSearchRequest):
    return knowledge_base.search_tracks(
        genre=req.genre,
        min_danceability=req.min_danceability or 0.0,
        min_energy=req.min_energy or 0.0, min_valence=req.min_valence or 0.0,
        tempo_range=tuple(req.tempo_range) if req.tempo_range else None,
        limit=req.limit,
    )


@router.post("/search", response_model=FullSearchResponse)
async def full_search(req: FullSearchRequest):
    return knowledge_base.full_search(
        query=req.query, search_type=req.search_type or "all",
        genre=req.genre, limit=req.limit, offset=req.offset,
    )


@router.get("/search-artists", response_model=list[ArtistSearchResult])
async def search_artists(q: str, lang: Optional[str] = None, limit: int = 10):
    if not q.strip():
        return []
    results = knowledge_base.search_artists(q.strip(), language=lang, limit=limit)
    return [ArtistSearchResult(**r) for r in results]


@router.get("/artist-stats", response_model=ArtistStats)
async def artist_stats(name: str, lang: Optional[str] = None):
    if not name.strip():
        raise HTTPException(status_code=400, detail="name is required")
    result = knowledge_base.get_artist_stats(name.strip(), language=lang)
    return ArtistStats(**result)


@router.get("/hit-profiles")
async def get_hit_profiles():
    profiles = knowledge_base.get_all_hit_profiles()
    return {"profiles": profiles, "count": len(profiles)}


@router.get("/hit-profiles/{genre}")
async def get_hit_profile(genre: str):
    profile = knowledge_base.get_hit_profile(genre)
    if not profile:
        raise HTTPException(status_code=404, detail=f"No hit profile found for genre: {genre}")
    return profile


@router.get("/genres")
async def get_genres():
    return {"genres": knowledge_base.get_genre_list()}


@router.get("/moods")
async def get_moods():
    return {"moods": list(MOOD_PRESETS.keys()), "features": MOOD_PRESETS}


@router.get("/genre-aliases")
async def get_genre_aliases():
    return {"aliases": {}}


@router.get("/stats")
async def get_kb_stats():
    return knowledge_base.get_stats()





@router.post("/load-ace-step")
async def load_ace_step():
    ace_ok = await ace_step.check_available()
    if not ace_ok:
        raise HTTPException(status_code=500, detail="ACE Step API not available. Start with: uv run acestep-api")
    if ace_step._models_initialized:
        return {"status": "available", "api_url": ace_step.ace_api_url, "models_initialized": True}
    success = await ace_step.load()
    if not success:
        raise HTTPException(status_code=500, detail="ACE Step initialization failed. Check VRAM and model paths.")
    return {"status": "available", "api_url": ace_step.ace_api_url, "models_initialized": True}


@router.post("/check-lm-studio")
async def check_lm_studio():
    available = await lm_studio.check_availability()
    models = await lm_studio.get_loaded_models() if available else []
    return {"available": available, "models": models}


@router.get("/model-profiles")
async def get_model_profiles():
    profiles = lm_studio.get_all_profiles()
    result = []
    for mid, p in profiles.items():
        result.append(ModelProfileSchema(
            model_id=p.model_id, display_name=p.display_name, family=p.family,
            context_window=p.context_window, max_output_tokens=p.max_output_tokens,
            optimal_temperature=p.optimal_temperature, json_reliability=p.json_reliability,
            instruction_following=p.instruction_following,
            needs_json_reinforcement=p.needs_json_reinforcement,
            needs_simple_prompts=p.needs_simple_prompts,
            supports_system_prompt=p.supports_system_prompt,
            tested_at=p.tested_at, auto_detected=p.auto_detected,
        ))
    return {"profiles": result, "active_model": lm_studio._model_id}


@router.put("/model-profiles/{model_id}")
async def update_model_profile(model_id: str, req: ModelProfileUpdateRequest):
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    profile = lm_studio.update_profile(model_id, updates)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Model profile not found: {model_id}")
    return ModelProfileSchema(
        model_id=profile.model_id, display_name=profile.display_name, family=profile.family,
        context_window=profile.context_window, max_output_tokens=profile.max_output_tokens,
        optimal_temperature=profile.optimal_temperature, json_reliability=profile.json_reliability,
        instruction_following=profile.instruction_following,
        needs_json_reinforcement=profile.needs_json_reinforcement,
        needs_simple_prompts=profile.needs_simple_prompts,
        supports_system_prompt=profile.supports_system_prompt,
        tested_at=profile.tested_at, auto_detected=profile.auto_detected,
    )


@router.post("/model-profiles/auto-detect")
async def auto_detect_model_profiles():
    new_models = await lm_studio.scan_and_build_profiles()
    return {"new_profiles": new_models, "total_profiles": len(lm_studio.get_all_profiles())}
