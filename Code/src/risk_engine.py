"""Risk evaluation engine — scores frames based on detected objects and zones."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.detector import Detection
from src.roi_config import ROIConfig


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class RiskEvent:
    """A single risk event for a detected class in a zone."""

    risk_type: str
    score: float
    level: str
    zone: str


@dataclass
class FrameRisk:
    """Aggregated risk assessment for one video frame."""

    frame_idx: int
    score: float
    level: str
    active_risks: list[RiskEvent] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _level_name(score: float) -> str:
    """Map a numeric score to a risk level string."""
    if score < 20.0:
        return "low"
    if score < 60.0:
        return "medium"
    return "high"


_AREA_DIVISOR: float = 0.05
_COOLDOWN_DAMPEN_CEILING: float = 59.5


# ---------------------------------------------------------------------------
# RiskEngine
# ---------------------------------------------------------------------------

class RiskEngine:
    """Scores frames by combining detection confidence, persistence, area, and ROI zones."""

    def __init__(
        self,
        classes_config: dict,
        roi_config: ROIConfig,
        score_history_window: int = 30,
        alert_cooldown_sec: float = 5.0,
        min_detection_area_ratio: float = 0.001,
    ) -> None:
        self._roi = roi_config
        self._window = max(1, score_history_window)
        self._cooldown_sec = alert_cooldown_sec
        self._min_area_ratio = min_detection_area_ratio

        # Parse class config → {name: {risk_weight, persistence_sec}}
        self._class_cfg: dict[str, dict[str, float]] = {}
        raw_classes = classes_config.get("classes", {})
        # Handle both list-of-dicts and dict-of-dicts formats
        if isinstance(raw_classes, dict):
            entries = list(raw_classes.values())
        else:
            entries = raw_classes
        for entry in entries:
            name = entry["name"]
            self._class_cfg[name] = {
                "risk_weight": float(entry.get("risk_weight", 0.0)),
                "persistence_sec": float(entry.get("persistence_sec", 0.0)),
            }

        # Per-class persistence tracking
        self._accumulated: dict[str, float] = {}
        self._last_seen: dict[str, float] = {}

        # History smoothing
        self._history: list[float] = []

        # Cooldown
        self._last_alert_time: float = float("-inf")

    # ------------------------------------------------------------------
    # evaluate
    # ------------------------------------------------------------------

    def evaluate(
        self,
        frame_idx: int,
        detections: list[Detection],
        timestamp_sec: float,
    ) -> FrameRisk:
        """Score one frame and return a FrameRisk assessment."""

        # --- Gather detections inside ROI zones ---
        inside: list[Detection] = [
            d for d in detections if self._roi.is_inside_any(d.center)
        ]

        # --- Per-class scoring ---
        class_scores: dict[str, float] = {}
        class_zones: dict[str, str] = {}

        for det in inside:
            cls = det.cls_name

            cfg = self._class_cfg.get(cls)
            if cfg is None:
                continue

            weight = cfg["risk_weight"]
            persistence_sec = cfg["persistence_sec"]

            # --- Persistence tracking ---
            prev_seen = self._last_seen.get(cls)
            if prev_seen is not None:
                delta = timestamp_sec - prev_seen
                self._accumulated[cls] = self._accumulated.get(cls, 0.0) + delta

            self._last_seen[cls] = timestamp_sec
            accumulated = self._accumulated.get(cls, 0.0)

            if persistence_sec > 0.0:
                duration_factor = min(1.0, accumulated / persistence_sec)
            else:
                duration_factor = 1.0

            # --- Area factor ---
            area_factor = min(1.0, det.area_ratio / _AREA_DIVISOR)

            # --- Raw score ---
            raw = weight * det.conf * duration_factor * area_factor * 100.0
            raw = max(0.0, min(100.0, raw))

            # Keep the best (highest) score per class
            prev_best = class_scores.get(cls, 0.0)
            if raw > prev_best:
                class_scores[cls] = raw
                # Zone lookup for this detection
                zone_name = "unknown"
                for zlabel in self._roi.get_zone_labels():
                    if self._roi.is_inside(zlabel, det.center):
                        zone_name = zlabel
                        break
                class_zones[cls] = zone_name

        # --- Frame-level raw score (max across classes) ---
        if class_scores:
            raw_frame_score = max(class_scores.values())
        else:
            raw_frame_score = 0.0

        # --- History smoothing (store raw, not dampened) ---
        self._history.append(raw_frame_score)
        if len(self._history) > self._window:
            self._history = self._history[-self._window:]

        smoothed = sum(self._history) / len(self._history) if self._history else 0.0

        # --- Cooldown dampening (after smoothing) ---
        in_cooldown = (timestamp_sec - self._last_alert_time) < self._cooldown_sec
        was_high = raw_frame_score >= 60.0

        if was_high and not in_cooldown:
            self._last_alert_time = timestamp_sec

        final_score = smoothed
        if in_cooldown and final_score >= 60.0:
            final_score = _COOLDOWN_DAMPEN_CEILING

        # --- Build active risks ---
        active_risks: list[RiskEvent] = []
        for cls, score in class_scores.items():
            level = _level_name(score)
            zone = class_zones.get(cls, "unknown")
            active_risks.append(RiskEvent(risk_type=cls, score=score, level=level, zone=zone))

        return FrameRisk(
            frame_idx=frame_idx,
            score=final_score,
            level=_level_name(final_score),
            active_risks=active_risks,
        )
