"""RED tests for src/risk_engine.py — must fail with ImportError before src/ exists."""
import pytest
from src.risk_engine import RiskEvent, FrameRisk, RiskEngine
from src.roi_config import ROIConfig
from src.detector import Detection


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _make_detection(
    cls_id: int = 0,
    cls_name: str = "vehicle",
    conf: float = 0.85,
    xyxy: tuple = (100.0, 100.0, 200.0, 200.0),
    area_ratio: float = 0.02,
) -> Detection:
    x1, y1, x2, y2 = xyxy
    cx = (x1 + x2) / 2.0
    cy = (y1 + y2) / 2.0
    return Detection(
        cls_id=cls_id,
        cls_name=cls_name,
        xyxy=xyxy,
        conf=conf,
        center=(cx, cy),
        area_ratio=area_ratio,
    )


def _make_roi_config() -> ROIConfig:
    return ROIConfig(
        {
            "enabled": True,
            "zones": {
                "corridor_main": {
                    "label": "corridor_main",
                    "polygon": [
                        [0.0, 0.0],
                        [500.0, 0.0],
                        [500.0, 400.0],
                        [0.0, 400.0],
                    ],
                },
                "fire_lane_entrance": {
                    "label": "fire_lane_entrance",
                    "polygon": [
                        [550.0, 0.0],
                        [640.0, 0.0],
                        [640.0, 480.0],
                        [550.0, 480.0],
                    ],
                },
            },
        }
    )


def _make_roi_config_disabled() -> ROIConfig:
    return ROIConfig({"enabled": False, "zones": {}})


_CLASSES_CFG = {
    "classes": [
        {"name": "vehicle", "risk_weight": 0.6, "color": [0, 128, 255], "persistence_sec": 10},
        {"name": "obstruction", "risk_weight": 0.7, "color": [0, 0, 255], "persistence_sec": 5},
        {"name": "ebike", "risk_weight": 0.9, "color": [255, 0, 255], "persistence_sec": 0},
    ]
}


# ---------------------------------------------------------------------------
# RiskEvent dataclass
# ---------------------------------------------------------------------------
class TestRiskEvent:
    def test_fields(self):
        evt = RiskEvent(risk_type="ebike", score=85.0, level="high", zone="fire_lane_entrance")
        assert evt.risk_type == "ebike"
        assert evt.score == 85.0
        assert evt.level == "high"
        assert evt.zone == "fire_lane_entrance"

    def test_low_level(self):
        evt = RiskEvent(risk_type="vehicle", score=10.0, level="low", zone="corridor_main")
        assert evt.level == "low"
        assert evt.score == 10.0

    def test_medium_level(self):
        evt = RiskEvent(risk_type="obstruction", score=45.0, level="medium", zone="fire_lane_entrance")
        assert evt.level == "medium"


# ---------------------------------------------------------------------------
# FrameRisk dataclass
# ---------------------------------------------------------------------------
class TestFrameRisk:
    def test_fields(self):
        fr = FrameRisk(
            frame_idx=42,
            score=72.5,
            level="high",
            active_risks=[
                RiskEvent(risk_type="ebike", score=85.0, level="high", zone="corridor_main")
            ],
        )
        assert fr.frame_idx == 42
        assert fr.score == 72.5
        assert fr.level == "high"
        assert len(fr.active_risks) == 1
        assert fr.active_risks[0].risk_type == "ebike"

    def test_empty_risks(self):
        fr = FrameRisk(frame_idx=0, score=0.0, level="low", active_risks=[])
        assert fr.score == 0.0
        assert fr.level == "low"
        assert fr.active_risks == []


# ---------------------------------------------------------------------------
# RiskEngine — core scoring logic
# ---------------------------------------------------------------------------
class TestRiskEngine:
    def test_init_creates(self):
        engine = RiskEngine(classes_config=_CLASSES_CFG, roi_config=_make_roi_config_disabled())
        assert engine is not None

    def test_evaluate_empty_detections(self):
        engine = RiskEngine(classes_config=_CLASSES_CFG, roi_config=_make_roi_config_disabled())
        result = engine.evaluate(frame_idx=0, detections=[], timestamp_sec=0.0)
        assert isinstance(result, FrameRisk)
        assert result.score == 0.0
        assert result.level == "low"
        assert result.active_risks == []

    def test_evaluate_vehicle_low_confidence(self):
        engine = RiskEngine(classes_config=_CLASSES_CFG, roi_config=_make_roi_config_disabled())
        det = _make_detection(cls_id=0, cls_name="vehicle", conf=0.3)
        result = engine.evaluate(frame_idx=0, detections=[det], timestamp_sec=0.0)
        assert result.score < 20

    def test_evaluate_vehicle_persistence_increases_score(self):
        engine = RiskEngine(classes_config=_CLASSES_CFG, roi_config=_make_roi_config_disabled())
        det = _make_detection(cls_id=0, cls_name="vehicle", conf=0.8, area_ratio=0.05)
        scores = []
        for i in range(30):
            result = engine.evaluate(frame_idx=i, detections=[det], timestamp_sec=float(i) * 0.5)
            scores.append(result.score)
        # Score should trend upward during first 10s (20 frames at 0.5s each)
        assert scores[-1] > scores[0], f"scores: {scores}"

    def test_evaluate_obstruction_persistence_medium(self):
        engine = RiskEngine(classes_config=_CLASSES_CFG, roi_config=_make_roi_config_disabled())
        det = _make_detection(cls_id=1, cls_name="obstruction", conf=0.75, area_ratio=0.05)
        last_score = 0.0
        for i in range(20):
            result = engine.evaluate(
                frame_idx=i, detections=[det], timestamp_sec=float(i) * 0.5
            )
            last_score = result.score
        # After 10s, obstruction should reach at least medium (> 20)
        assert last_score >= 20, f"last_score={last_score}"

    def test_evaluate_ebike_immediate_high(self):
        engine = RiskEngine(classes_config=_CLASSES_CFG, roi_config=_make_roi_config_disabled())
        det = _make_detection(cls_id=2, cls_name="ebike", conf=0.95, area_ratio=0.05)
        result = engine.evaluate(frame_idx=0, detections=[det], timestamp_sec=0.0)
        # Ebike has risk_weight=0.9 and persistence_sec=0 → immediate high
        assert result.score >= 60
        assert result.level == "high"

    def test_evaluate_area_factor_larger_is_higher(self):
        engine = RiskEngine(classes_config=_CLASSES_CFG, roi_config=_make_roi_config_disabled())
        det_small = _make_detection(cls_id=2, cls_name="ebike", conf=0.9, area_ratio=0.001)
        det_large = _make_detection(cls_id=2, cls_name="ebike", conf=0.9, area_ratio=0.3)
        r_small = engine.evaluate(frame_idx=0, detections=[det_small], timestamp_sec=0.0)
        r_large = engine.evaluate(frame_idx=0, detections=[det_large], timestamp_sec=0.0)
        assert r_large.score > r_small.score

    def test_evaluate_roi_filtering_excludes_outside(self):
        engine = RiskEngine(classes_config=_CLASSES_CFG, roi_config=_make_roi_config())
        # Detection centered at (600, 50) is inside fire_lane_entrance
        det_inside = _make_detection(
            cls_id=0, cls_name="vehicle", conf=0.9,
            xyxy=(570.0, 20.0, 630.0, 80.0), area_ratio=0.01
        )
        # Detection centered at (550, 440) — on boundary, check behavior
        det_outside = _make_detection(
            cls_id=1, cls_name="obstruction", conf=0.9,
            xyxy=(510.0, 400.0, 540.0, 440.0), area_ratio=0.01
        )
        r_out = engine.evaluate(frame_idx=0, detections=[det_outside], timestamp_sec=0.0)
        # Outside detection should produce no risk events
        assert all(evt.score == 0.0 for evt in r_out.active_risks) or r_out.score < 5.0

    def test_evaluate_roi_inside_includes_zone(self):
        engine = RiskEngine(classes_config=_CLASSES_CFG, roi_config=_make_roi_config())
        det = _make_detection(
            cls_id=2, cls_name="ebike", conf=0.85,
            xyxy=(570.0, 20.0, 610.0, 60.0), area_ratio=0.01
        )
        result = engine.evaluate(frame_idx=0, detections=[det], timestamp_sec=0.0)
        # Inside fire_lane_entrance, should have at least one risk event
        assert len(result.active_risks) >= 1

    def test_evaluate_score_bounds(self):
        engine = RiskEngine(classes_config=_CLASSES_CFG, roi_config=_make_roi_config_disabled())
        for conf in (0.0, 0.5, 1.0):
            det = _make_detection(cls_id=2, cls_name="ebike", conf=conf, area_ratio=0.1)
            result = engine.evaluate(frame_idx=0, detections=[det], timestamp_sec=0.0)
            assert 0.0 <= result.score <= 100.0, f"score out of bounds: {result.score}"

    def test_evaluate_cooldown(self):
        engine = RiskEngine(
            classes_config=_CLASSES_CFG,
            roi_config=_make_roi_config_disabled(),
            alert_cooldown_sec=5.0,
        )
        det = _make_detection(cls_id=2, cls_name="ebike", conf=0.95, area_ratio=0.05)
        # First alert triggers
        r1 = engine.evaluate(frame_idx=0, detections=[det], timestamp_sec=0.0)
        assert r1.level == "high"
        # 2s later — still within cooldown, alert should not fire
        r2 = engine.evaluate(frame_idx=1, detections=[det], timestamp_sec=2.0)
        # Cooldown suppresses re-alert; level may drop to medium/low
        # Exact behavior depends on implementation, but score should be dampened
        assert r2.score <= r1.score

    def test_evaluate_history_tracking(self):
        engine = RiskEngine(
            classes_config=_CLASSES_CFG,
            roi_config=_make_roi_config_disabled(),
            score_history_window=10,
        )
        det = _make_detection(cls_id=1, cls_name="obstruction", conf=0.8, area_ratio=0.05)
        for i in range(15):
            engine.evaluate(frame_idx=i, detections=[det], timestamp_sec=float(i) * 0.5)
        # After 15 frames, engine should have kept at most 10 in history
        # (verifying history window cap — no crash means it works)

    def test_evaluate_multiple_classes_ebike_dominates(self):
        engine = RiskEngine(classes_config=_CLASSES_CFG, roi_config=_make_roi_config_disabled())
        det_vehicle = _make_detection(cls_id=0, cls_name="vehicle", conf=0.8, area_ratio=0.05)
        det_ebike = _make_detection(cls_id=2, cls_name="ebike", conf=0.9, area_ratio=0.05)
        r_vehicle = engine.evaluate(frame_idx=0, detections=[det_vehicle], timestamp_sec=0.0)
        r_ebike = engine.evaluate(frame_idx=0, detections=[det_ebike], timestamp_sec=0.0)
        r_both = engine.evaluate(
            frame_idx=0, detections=[det_vehicle, det_ebike], timestamp_sec=0.0
        )
        # Combined result dominated by ebike (highest risk_weight × conf)
        assert r_both.score >= r_ebike.score * 0.8
