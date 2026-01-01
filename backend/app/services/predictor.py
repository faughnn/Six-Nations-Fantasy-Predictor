from typing import Optional, Dict, Any, List
import os
import numpy as np
from dataclasses import dataclass

# Try to import ML libraries, but make them optional for testing
try:
    import joblib
    JOBLIB_AVAILABLE = True
except ImportError:
    JOBLIB_AVAILABLE = False

from app.config import get_settings


@dataclass
class PlayerFeatures:
    """Features for ML prediction"""
    # Rolling averages
    tries_last_3: float = 0.0
    tries_last_5: float = 0.0
    tackles_last_3: float = 0.0
    tackles_last_5: float = 0.0
    metres_last_3: float = 0.0
    metres_last_5: float = 0.0
    turnovers_last_3: float = 0.0
    fantasy_points_last_3: float = 0.0
    fantasy_points_last_5: float = 0.0

    # Player attributes
    is_kicker: bool = False
    is_forward: bool = False

    # Fixture features
    is_home: bool = True
    is_starting: bool = True

    # Odds features
    anytime_try_odds: Optional[float] = None

    def to_array(self) -> np.ndarray:
        """Convert features to numpy array for prediction"""
        return np.array([
            self.tries_last_3,
            self.tries_last_5,
            self.tackles_last_3,
            self.tackles_last_5,
            self.metres_last_3,
            self.metres_last_5,
            self.turnovers_last_3,
            self.fantasy_points_last_3,
            self.fantasy_points_last_5,
            float(self.is_kicker),
            float(self.is_forward),
            float(self.is_home),
            float(self.is_starting),
            self.anytime_try_odds or 0.0,
        ])


class Predictor:
    """ML model for predicting fantasy points"""

    def __init__(self, model_path: Optional[str] = None):
        self.model = None
        self.model_path = model_path or get_settings().model_path
        self._load_model()

    def _load_model(self):
        """Load the trained model from disk"""
        if JOBLIB_AVAILABLE and os.path.exists(self.model_path):
            try:
                self.model = joblib.load(self.model_path)
            except Exception:
                self.model = None

    def predict(self, features: PlayerFeatures) -> Dict[str, Any]:
        """
        Predict fantasy points for a player.

        Returns:
            dict with predicted_points, confidence_lower, confidence_upper
        """
        if self.model is None:
            # Fallback to heuristic prediction
            return self._heuristic_predict(features)

        X = features.to_array().reshape(1, -1)
        prediction = float(self.model.predict(X)[0])

        # Estimate confidence interval (simplified)
        std_estimate = max(3.0, prediction * 0.2)

        return {
            "predicted_points": prediction,
            "confidence_lower": prediction - 1.645 * std_estimate,
            "confidence_upper": prediction + 1.645 * std_estimate,
        }

    def _heuristic_predict(self, features: PlayerFeatures) -> Dict[str, Any]:
        """
        Heuristic prediction when no ML model is available.
        Based on historical averages and simple weighting.
        """
        # Base prediction on recent form
        base_points = features.fantasy_points_last_3 * 0.6 + features.fantasy_points_last_5 * 0.4

        # If no history, use position-based defaults
        if base_points == 0:
            if features.is_forward:
                base_points = 12.0  # Forwards average
            else:
                base_points = 15.0  # Backs average

        # Adjustments
        if features.is_kicker:
            base_points += 3.0

        if not features.is_starting:
            base_points *= 0.4  # Bench players get fewer minutes

        if not features.is_home:
            base_points *= 0.95  # Slight away penalty

        # Adjust based on try odds if available
        if features.anytime_try_odds and features.anytime_try_odds > 0:
            try_prob = 1.0 / features.anytime_try_odds
            if features.is_forward:
                base_points += try_prob * 15 * 0.3  # Expected try points contribution
            else:
                base_points += try_prob * 10 * 0.3

        # Confidence interval
        std_estimate = max(3.0, base_points * 0.2)

        return {
            "predicted_points": round(base_points, 2),
            "confidence_lower": round(base_points - 1.645 * std_estimate, 2),
            "confidence_upper": round(base_points + 1.645 * std_estimate, 2),
        }

    def predict_batch(self, features_list: List[PlayerFeatures]) -> List[Dict[str, Any]]:
        """Predict for multiple players"""
        return [self.predict(f) for f in features_list]

    def get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance from the model"""
        if self.model is None:
            return {}

        feature_names = [
            "tries_last_3", "tries_last_5", "tackles_last_3", "tackles_last_5",
            "metres_last_3", "metres_last_5", "turnovers_last_3",
            "fantasy_points_last_3", "fantasy_points_last_5",
            "is_kicker", "is_forward", "is_home", "is_starting", "anytime_try_odds"
        ]

        try:
            if hasattr(self.model, 'feature_importances_'):
                importances = self.model.feature_importances_
            elif hasattr(self.model, 'named_steps') and hasattr(self.model.named_steps.get('model', {}), 'feature_importances_'):
                importances = self.model.named_steps['model'].feature_importances_
            else:
                return {}

            return dict(zip(feature_names, importances))
        except Exception:
            return {}
