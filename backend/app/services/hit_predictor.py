import logging
import numpy as np
from typing import Optional
from backend.app.core.database import SessionLocal
from backend.app.models.tables import Track

logger = logging.getLogger("spotigem.hit_predictor")


class HitPredictorService:
    def __init__(self):
        self._feature_means = None
        self._feature_stds = None
        self._fitted = False

    def _compute_benchmark_stats(self):
        db = SessionLocal()
        try:
            popular = db.query(Track).filter(Track.is_popular == True).all()
            if not popular:
                return
            features = []
            for t in popular:
                features.append([t.danceability or 0, t.energy or 0, t.valence or 0, (t.tempo or 0) / 200.0, (t.loudness or 0) / -60.0, t.speechiness or 0, t.acousticness or 0, t.instrumentalness or 0, t.liveness or 0])
            arr = np.array(features)
            self._feature_means = np.mean(arr, axis=0)
            self._feature_stds = np.std(arr, axis=0) + 1e-8
            self._fitted = True
        finally:
            db.close()

    def predict(self, audio_features: dict, genre: Optional[str] = None) -> dict:
        if not self._fitted:
            self._compute_benchmark_stats()
        if not self._fitted:
            return {"hit_score": 0.5, "hit_label": "insufficient_data", "confidence": 0.0, "recommendations": [], "reference_tracks": []}

        feature_vec = np.array([audio_features.get("danceability", 0.5), audio_features.get("energy", 0.5), audio_features.get("valence", 0.5), audio_features.get("tempo", 120) / 200.0, audio_features.get("loudness", -6) / -60.0, audio_features.get("speechiness", 0.05), audio_features.get("acousticness", 0.1), audio_features.get("instrumentalness", 0.0), audio_features.get("liveness", 0.1)])
        distances = np.abs(feature_vec - self._feature_means) / self._feature_stds
        avg_distance = np.mean(distances)
        raw_score = max(0, 1.0 - avg_distance / 3.0)
        hit_score = float(np.clip(raw_score, 0, 1))

        if hit_score >= 0.7:
            hit_label = "potential_hit"
        elif hit_score >= 0.4:
            hit_label = "moderate"
        else:
            hit_label = "low"

        confidence = float(np.clip(1.0 - np.mean(self._feature_stds) / 0.5, 0, 1))
        recommendations = self._generate_recommendations(feature_vec, distances)

        return {"hit_score": round(hit_score, 4), "hit_label": hit_label, "confidence": round(confidence, 4), "recommendations": recommendations}

    def compare_with_reference(self, audio_features: dict, similar_tracks: list[dict]) -> dict:
        if not similar_tracks:
            return {"closest_match": None, "differences": [], "overall_similarity": 0}
        feature_names = ["danceability", "energy", "valence", "tempo", "loudness", "speechiness", "acousticness", "instrumentalness", "liveness"]
        vec = np.array([audio_features.get(k, 0.5) for k in feature_names])
        vec[3] /= 200.0; vec[4] = abs(vec[4]) / 60.0

        best = similar_tracks[0]
        ref_vec = np.array([best.get(k, 0.5) for k in feature_names])
        ref_vec[3] /= 200.0; ref_vec[4] = abs(ref_vec[4]) / 60.0

        diff = vec - ref_vec
        similarity = float(np.clip(1.0 - np.linalg.norm(diff) / 3.0, 0, 1))
        differences = []
        for i, name in enumerate(feature_names):
            if abs(diff[i]) > 0.1:
                direction = "higher" if diff[i] > 0 else "lower"
                differences.append(f"{name} is {abs(diff[i]):.2f} points {direction} than '{best.get('track_name','?')}'")

        return {"closest_match": {"track_name": best.get("track_name"), "artist_name": best.get("artist_name"), "similarity_score": best.get("similarity_score", 0)}, "differences": differences[:5], "overall_similarity": round(similarity, 3)}

    def _generate_recommendations(self, feature_vec: np.ndarray, distances: np.ndarray) -> list[str]:
        feature_names = ["danceability", "energy", "valence", "tempo", "loudness", "speechiness", "acousticness", "instrumentalness", "liveness"]
        recs = []
        top_deviations = np.argsort(distances)[-3:][::-1]
        for idx in top_deviations:
            if distances[idx] > 1.5:
                name = feature_names[idx]
                current = feature_vec[idx]
                target = self._feature_means[idx]
                if name == "tempo":
                    current *= 200; target *= 200
                    recs.append(f"Adjust tempo from {current:.0f} BPM closer to hit average of {target:.0f} BPM")
                elif name == "loudness":
                    current *= -60; target *= -60
                    recs.append(f"Adjust loudness from {current:.1f} dB closer to hit average of {target:.1f} dB")
                else:
                    recs.append(f"Adjust {name} from {current:.2f} closer to hit average of {target:.2f}")
        return recs
