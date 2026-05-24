# SpotiGem - Project Knowledge

## Pipeline Architecture

The generation pipeline wires all 4 services together with real data:

```
GenerateRequest(prompt, genre, mood)
  → KnowledgeBase.get_reference_package(genre, mood, features))
    → Gets similar_tracks (top-5 by feature vector distance from DB)
    → Gets lyrics_samples (from actual hit songs in same genre)
    → Gets hit_profile (genre averages from popular tracks)
  → LMStudio.craft_prompt(reference_package, user_prompt)
    → Returns {prompt, bpm, key_scale, time_signature, lyrics_template}
    → JSON-structured response, fed reference tracks + lyrics examples
  → ACE Step.generate(prompt, bpm, key_scale, lyrics)
    → Audio generation with exact musical parameters
  → HitPredictor.predict(features) + compare_with_reference(similar_tracks)
    → Hit score vs genre benchmark
    → Comparison saying "this is closer to X than Y because..."
```

Result includes `PipelineTrace` with:
- `reference_tracks[]` - which real Spotify tracks were used
- `lyrics_samples[]` - real hit lyrics for style reference
- `hit_profile_used` - genre averages
- `lm_params` - {bpm, key_scale, time_signature}
- `comparison` - {closest_match, differences[], overall_similarity}

## Key Files Changed Today (2026-05-21 - afternoon)
- `backend/app/api/router.py`: Added `_prompt_features()` — keyword-based feature extraction from prompt text (replaces `_mood_features()`). Now "montagem supersonic" → high tempo (150), high energy, low acousticness. Also passes `record_id` to ACE Step for filename.
- `backend/app/services/ace_step.py`: Filename uses `track_{record_id}.mp3` instead of `spotigem_{timestamp}.mp3`
- `backend/app/services/knowledge_base.py`: `get_similar_tracks()` now returns `duration_ms` for auto-duration calculation
- `frontend/src/pages/GeneratePage.tsx`: "Use this prompt" button on Preview; prompt changes auto-clear stale state; "Clear" button for lyrics; auto-duration display
- `frontend/src/lib/api.ts`: Added `lyrics_template` to PipelineTrace lm_params type

## Key Files Changed Today (2026-05-21 - morning)
- `backend/app/schemas/schemas.py`: Added ReferenceTrack, LyricSample, PipelineTrace; added `mood`, `reference_track_ids` to GenerateRequest; added `pipeline_trace` to GenerateResponse
- `backend/app/models/tables.py`: Replaced target_* columns with `mood`, `pipeline_trace` (JSON text), `ace_params` (JSON text) in GeneratedTrack
- `backend/app/services/knowledge_base.py`: Added get_similar_tracks(), get_lyrics_by_genre(), get_reference_package() — all using real vector similarity
- `backend/app/services/lm_studio.py`: Replaced generate_hit_prompt() with craft_prompt() that takes reference_package and returns structured JSON {prompt, bpm, key_scale, time_signature, lyrics_template}
- `backend/app/services/hit_predictor.py`: Added compare_with_reference() — compares generated features against nearest real tracks
- `backend/app/api/router.py`: New _generate_audio_pipeline() — full pipeline KB→LM→ACE→Predictor; stores pipeline_trace as JSON
- `frontend/src/lib/api.ts`: Added ReferenceTrack, LyricSample, PipelineTrace types; updated GenerateRequest/Response
- `frontend/src/pages/GeneratePage.tsx`: Added mood selector; shows pipeline trace (reference tracks, LM params, comparison) after generation

## Python Venv
```powershell
venv\Scripts\python.exe -m ...
```

## Common Commands
```powershell
# Start backend + frontend
.\run.bat

# Start ACE Step separately (must be running before generate)
cd ace-step-official
uv run acestep-api

# Frontend build check
cd frontend
npm.cmd run build

# Backend test
venv\Scripts\python.exe -m pytest
```
