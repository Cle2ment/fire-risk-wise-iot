"""YOLO-based object detector producing Detection dataclass instances."""

import os
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import yaml
from ultralytics import YOLO


@dataclass
class Detection:
    """Single object detection result with bounding box and metadata."""

    cls_id: int
    cls_name: str
    xyxy: tuple[float, float, float, float]
    conf: float
    center: tuple[float, float] = (0.0, 0.0)
    area_ratio: float = 0.0


class Detector:
    """YOLO-based object detector with configurable thresholds."""

    def __init__(
        self,
        model_path: str,
        imgsz: int = 640,
        conf_thresh: float = 0.25,
        iou_thresh: float = 0.45,
        device: str = "cpu",
    ) -> None:
        if not os.path.isfile(model_path):
            raise FileNotFoundError(f"Model not found: {model_path}")

        self.imgsz = imgsz
        self.conf_thresh = conf_thresh
        self.iou_thresh = iou_thresh
        self.device = device

        # Access ultralytics.YOLO via module attribute so monkeypatch works.
        import ultralytics as _ultralytics

        self._model = _ultralytics.YOLO(model_path)
        self._class_names = _load_class_names()

    def detect(self, frame: np.ndarray) -> list[Detection]:
        """Run detection on *frame* and return filtered :class:`Detection` list."""
        h, w = frame.shape[:2]
        if h == 0 or w == 0:
            return []

        # Use .__call__() so tests can override __call__ on the instance.
        results = self._model(frame)
        frame_area = float(w * h)
        detections: list[Detection] = []

        for result in results:
            boxes = result.boxes
            if boxes is None or len(boxes.cls) == 0:
                continue

            for i in range(len(boxes.cls)):
                conf = float(boxes.conf[i])
                if conf < self.conf_thresh:
                    continue

                x1 = float(boxes.xyxy[i][0])
                y1 = float(boxes.xyxy[i][1])
                x2 = float(boxes.xyxy[i][2])
                y2 = float(boxes.xyxy[i][3])
                cls_id = int(boxes.cls[i])

                cx = (x1 + x2) / 2.0
                cy = (y1 + y2) / 2.0
                box_area = (x2 - x1) * (y2 - y1)
                area_ratio = box_area / frame_area if frame_area > 0 else 0.0
                cls_name = self._class_names.get(cls_id, f"unknown_{cls_id}")

                detections.append(
                    Detection(
                        cls_id=cls_id,
                        cls_name=cls_name,
                        xyxy=(x1, y1, x2, y2),
                        conf=conf,
                        center=(cx, cy),
                        area_ratio=area_ratio,
                    )
                )

        return detections


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_class_names() -> dict[int, str]:
    """Load class-id → name mapping from ``configs/classes.yaml``."""
    config_path = Path(__file__).parent.parent / "configs" / "classes.yaml"
    if not config_path.is_file():
        return {}

    with open(config_path, encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}

    mapping: dict[int, str] = {}
    for k, v in raw.get("classes", {}).items():
        mapping[int(k)] = v.get("name", f"class_{k}")
    return mapping
