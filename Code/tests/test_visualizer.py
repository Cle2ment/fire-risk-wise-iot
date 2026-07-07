"""RED tests for src/visualizer.py — must fail with ImportError before src/ exists."""
import numpy as np
import pytest
from src.visualizer import Visualizer
from src.detector import Detection
from src.risk_engine import RiskEvent, FrameRisk


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def dummy_frame() -> np.ndarray:
    return np.zeros((480, 640, 3), dtype=np.uint8)


@pytest.fixture
def sample_detections() -> list[Detection]:
    return [
        Detection(cls_id=0, cls_name="vehicle", xyxy=(50., 60., 150., 180.),
                  conf=0.85, center=(100., 120.), area_ratio=0.04),
        Detection(cls_id=2, cls_name="ebike", xyxy=(400., 200., 520., 350.),
                  conf=0.95, center=(460., 275.), area_ratio=0.06),
    ]


@pytest.fixture
def sample_frame_risk() -> FrameRisk:
    return FrameRisk(
        frame_idx=0,
        score=75.0,
        level="high",
        active_risks=[
            RiskEvent(risk_type="ebike", score=85.0, level="high", zone="corridor_main"),
            RiskEvent(risk_type="vehicle", score=35.0, level="medium", zone="fire_lane_entrance"),
        ],
    )


# ---------------------------------------------------------------------------
# Visualizer
# ---------------------------------------------------------------------------
class TestVisualizer:
    def test_init_creates(self):
        vis = Visualizer()
        assert vis is not None

    def test_draw_returns_same_shape(self, dummy_frame, sample_detections, sample_frame_risk):
        vis = Visualizer()
        result = vis.draw(dummy_frame, sample_detections, sample_frame_risk, fps=30.0)
        assert isinstance(result, np.ndarray)
        assert result.shape == dummy_frame.shape

    def test_draw_returns_uint8(self, dummy_frame, sample_detections, sample_frame_risk):
        vis = Visualizer()
        result = vis.draw(dummy_frame, sample_detections, sample_frame_risk, fps=15.5)
        assert result.dtype == np.uint8

    def test_draw_empty_detections(self, dummy_frame):
        vis = Visualizer()
        result = vis.draw(
            dummy_frame,
            [],
            FrameRisk(frame_idx=1, score=0.0, level="low", active_risks=[]),
            fps=30.0,
        )
        assert result.shape == dummy_frame.shape

    def test_draw_preserves_original(self, dummy_frame, sample_detections, sample_frame_risk):
        vis = Visualizer()
        _ = vis.draw(dummy_frame, sample_detections, sample_frame_risk, fps=30.0)
        # original frame must not be mutated
        assert np.array_equal(dummy_frame, np.zeros((480, 640, 3), dtype=np.uint8))

    def test_dashboard_drawn(self, dummy_frame):
        """Top dashboard area should differ from a uniformly black frame."""
        vis = Visualizer()
        det = Detection(cls_id=2, cls_name="ebike", xyxy=(300., 200., 360., 280.),
                        conf=0.9, center=(330., 240.), area_ratio=0.02)
        fr = FrameRisk(frame_idx=0, score=45.0, level="medium",
                       active_risks=[RiskEvent(risk_type="ebike", score=45.0,
                                               level="medium", zone="corridor_main")])
        result = vis.draw(dummy_frame, [det], fr, fps=15.0)
        # Top portion (first 60 pixels) should contain non-black pixels
        dashboard_region = result[:60, :, :]
        assert np.any(dashboard_region > 0)

    def test_bbox_drawn(self, dummy_frame):
        """Detection boxes should produce visible pixels near the bbox edges."""
        vis = Visualizer()
        det = Detection(cls_id=0, cls_name="vehicle", xyxy=(100., 80., 300., 250.),
                        conf=0.88, center=(200., 165.), area_ratio=0.05)
        fr = FrameRisk(frame_idx=0, score=20.0, level="medium",
                       active_risks=[RiskEvent(risk_type="vehicle", score=20.0,
                                               level="medium", zone="corridor_main")])
        result = vis.draw(dummy_frame, [det], fr, fps=25.0)
        # The top edge of the bbox region should differ from the baseline (0)
        top_edge = result[80, 100:301, :]
        assert np.any(top_edge > 0)

    def test_status_bar_drawn(self, dummy_frame, sample_frame_risk):
        """Bottom status bar should contain rendered text."""
        vis = Visualizer()
        det = Detection(cls_id=0, cls_name="vehicle", xyxy=(50., 60., 150., 180.),
                        conf=0.85, center=(100., 120.), area_ratio=0.04)
        result = vis.draw(dummy_frame, [det], sample_frame_risk, fps=30.0)
        bottom = result[-30:, :, :]
        assert np.any(bottom > 0)
