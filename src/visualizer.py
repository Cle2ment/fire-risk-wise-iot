"""OpenCV-based frame visualizer: detection boxes, risk dashboard, status bar."""
import os

import numpy as np
import yaml

from src.detector import Detection
from src.risk_engine import FrameRisk
from src.utils import get_gradient_color

# ---------------------------------------------------------------------------
# class colour lookup
# ---------------------------------------------------------------------------
def _load_class_colours() -> dict[int, tuple[int, int, int]]:
    path = os.path.join(os.path.dirname(__file__), "..", "configs", "classes.yaml")
    colours: dict[int, tuple[int, int, int]] = {}
    try:
        with open(path, encoding="utf-8") as fh:
            cfg = yaml.safe_load(fh) or {}
        for key, val in cfg.get("classes", {}).items():
            colours[int(key)] = tuple(int(c) for c in val["color"])
    except (FileNotFoundError, KeyError, TypeError):
        pass
    return colours


_CLASS_COLOURS = _load_class_colours()
_DASHBOARD_H = 60
_STATUS_H = 30


class Visualizer:
    """Draws annotated output frame with bounding-boxes, dashboard, and status bar."""

    def __init__(self) -> None:
        pass

    def draw(
        self,
        frame: np.ndarray,
        detections: list[Detection],
        frame_risk: FrameRisk,
        fps: float,
    ) -> np.ndarray:
        import cv2

        canvas = frame.copy()
        h, w = canvas.shape[:2]

        # --- Detection bounding boxes ---
        for det in detections:
            colour = _CLASS_COLOURS.get(det.cls_id, (128, 128, 128))
            x1, y1, x2, y2 = (int(v) for v in det.xyxy)
            cv2.rectangle(canvas, (x1, y1), (x2, y2), colour, 2)

            lbl = f"{det.cls_name} {det.conf:.2f}"
            (tw, th), baseline = cv2.getTextSize(lbl, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(canvas, (x1, y1 - th - 4), (x1 + tw + 6, y1), colour, -1)
            cv2.putText(canvas, lbl, (x1 + 3, y1 - 4), cv2.FONT_HERSHEY_SIMPLEX,
                        0.5, (255, 255, 255), 1)

        # --- Dashboard (top overlay, draw directly on canvas) ---
        cv2.rectangle(canvas, (0, 0), (w, _DASHBOARD_H), (50, 50, 50), -1)
        cv2.putText(canvas, f"Risk Score: {frame_risk.score:.1f}",
                    (10, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        score_col = get_gradient_color(frame_risk.score)
        cv2.putText(canvas, frame_risk.level.upper(), (260, 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, score_col, 2)
        # gauge background
        cv2.rectangle(canvas, (10, 32), (w - 20, 52), (80, 80, 80), -1)
        fill_w = int((frame_risk.score / 100.0) * (w - 20))
        cv2.rectangle(canvas, (10, 32), (10 + fill_w, 52), score_col, -1)
        cv2.rectangle(canvas, (10, 32), (w - 20, 52), (180, 180, 180), 1)

        # --- Status bar (bottom overlay, draw directly on canvas) ---
        sy = h - _STATUS_H
        cv2.rectangle(canvas, (0, sy), (w, h), (30, 30, 30), -1)
        parts = [f"{e.risk_type}:{e.score:.0f}" for e in frame_risk.active_risks[:3]]
        cv2.putText(canvas, f"FPS:{fps:.1f}  {', '.join(parts)}",
                    (10, sy + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (220, 220, 220), 1)

        return canvas
