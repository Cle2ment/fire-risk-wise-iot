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
        # COCO model (80 classes) → apply mapping; fine-tuned (9 classes) → direct
        nc = getattr(self._model, "names", {})
        self._use_coco_map = len(nc) >= 50
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
                area_ratio_val = box_area / frame_area if frame_area > 0 else 0.0
                # COCO model: remap class IDs to fire-risk categories
                if self._use_coco_map:
                    fire_id = COCO_TO_FIRE.get(cls_id, -1)
                    if fire_id < 0:
                        continue
                    cls_name = self._class_names.get(fire_id, f"class_{fire_id}")
                else:
                    fire_id = cls_id
                    cls_name = self._class_names.get(cls_id, f"unknown_{cls_id}")
                detections.append(
                    Detection(
                        cls_id=fire_id,
                        cls_name=cls_name,
                        xyxy=(x1, y1, x2, y2),
                        conf=conf,
                        center=(cx, cy),
                        area_ratio=area_ratio_val,
                    )
                )

        return detections


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# COCO class-id → fire-risk class-id mapping
# COCO model outputs 0–79 IDs; this remaps to our 9 fire-risk categories.
# ---------------------------------------------------------------------------
COCO_TO_FIRE: dict[int, int] = {
    0: 6,    # person -> congested (people in cluttered areas = hazard)
    1: 2,    # bicycle -> ebike
    2: 0,    # car -> vehicle
    3: 2,    # motorcycle -> ebike
    4: 1,    # airplane -> obstruction (large object)
    5: 0,    # bus -> vehicle
    6: 1,    # train -> obstruction
    7: 0,    # truck -> vehicle
    8: 1,    # boat -> obstruction (large debris/clutter)
    9: 1,    # traffic light -> obstruction
   10: 1,    # fire hydrant -> obstruction
   11: 1,    # stop sign -> obstruction
   13: 1,    # bench -> obstruction (outdoor furniture blocking path)
   14: 3,    # bird -> debris_wood (nesting material)
   15: 4,    # cat -> debris_wood
   16: 3,    # dog -> debris_wood
   24: 5,    # backpack -> debris_mixed
   25: 5,    # umbrella -> debris_mixed
   26: 5,    # handbag -> debris_mixed
   27: 5,    # tie -> debris_mixed
   28: 5,    # suitcase -> debris_mixed
   31: 5,    # handbag(alt) -> debris_mixed
   32: 5,    # suitcase(alt) -> debris_mixed
   33: 5,    # frisbee -> debris_mixed
   34: 5,    # skis -> debris_wood
   35: 5,    # snowboard -> debris_wood
   36: 5,    # sports ball -> debris_mixed
   37: 5,    # kite -> debris_mixed
   38: 5,    # baseball bat -> debris_wood
   39: 7,    # bottle -> flammable_liquid
   40: 7,    # wine glass -> flammable_liquid
   41: 7,    # cup -> flammable_liquid
   42: 5,    # fork -> debris_mixed
   43: 5,    # knife -> debris_mixed
   44: 5,    # spoon -> debris_mixed
   45: 5,    # bowl -> debris_mixed
   46: 5,    # banana -> debris_mixed
   47: 5,    # apple -> debris_mixed
   48: 5,    # sandwich -> debris_mixed
   49: 5,    # orange -> debris_mixed
   50: 5,    # broccoli -> debris_mixed
   51: 5,    # carrot -> debris_mixed
   52: 5,    # hot dog -> debris_mixed
   53: 5,    # pizza -> debris_mixed
   54: 5,    # donut -> debris_mixed
   55: 5,    # cake -> debris_mixed
   56: 6,    # chair -> congested_space
   57: 6,    # couch -> congested_space
   58: 3,    # potted plant -> debris_wood
   59: 6,    # bed -> congested_space
   60: 6,    # dining table -> congested_space
   61: 1,    # toilet -> obstruction
   62: 8,    # tv -> electrical_hazard
   63: 8,    # laptop -> electrical_hazard
   64: 8,    # mouse -> electrical_hazard
   65: 8,    # remote -> electrical_hazard
   66: 8,    # keyboard -> electrical_hazard
   67: 8,    # cell phone -> electrical_hazard
   68: 8,    # microwave -> electrical_hazard
   69: 8,    # oven -> electrical_hazard
   70: 8,    # toaster -> electrical_hazard
   71: 1,    # sink -> obstruction
   72: 8,    # refrigerator -> electrical_hazard
   73: 4,    # book -> debris_paper
   74: 5,    # clock -> debris_mixed
   75: 5,    # vase -> debris_mixed
   76: 5,    # scissors -> debris_mixed
   77: 5,    # teddy bear -> debris_mixed
   78: 8,    # hair drier -> electrical_hazard
   79: 5,    # toothbrush -> debris_mixed
   80: 5,    # hair brush -> debris_mixed
   84: 4,    # book(alt) -> debris_paper
   85: 5,    # other -> debris_mixed
   86: 3,    # other -> debris_wood
}


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
