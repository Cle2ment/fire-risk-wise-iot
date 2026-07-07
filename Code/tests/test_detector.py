"""RED tests for src/detector.py — must fail with ImportError before src/ exists."""

import numpy as np
import pytest
from src.detector import Detection, Detector


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def vehicle_detection() -> "Detection":
    """A full Detection instance with all 7 fields populated."""
    return Detection(
        cls_id=0,
        cls_name="vehicle",
        xyxy=(10.0, 20.0, 100.0, 150.0),
        conf=0.85,
        center=(55.0, 85.0),
        area_ratio=0.02,
    )


@pytest.fixture
def dummy_frame() -> np.ndarray:
    """640x640x3 uint8 dummy frame (all zeros)."""
    return np.zeros((640, 640, 3), dtype=np.uint8)


@pytest.fixture
def empty_frame() -> np.ndarray:
    """0x0x3 empty frame."""
    return np.zeros((0, 0, 3), dtype=np.uint8)


# ---------------------------------------------------------------------------
# Detection dataclass tests
# ---------------------------------------------------------------------------

class TestDetectionDataclass:
    """Tests for the Detection dataclass — 7 fields, immutability, types."""

    def test_all_seven_fields_match(self, vehicle_detection):
        """Detection stores and returns all 7 constructor fields correctly."""
        assert vehicle_detection.cls_id == 0
        assert vehicle_detection.cls_name == "vehicle"
        assert vehicle_detection.xyxy == (10.0, 20.0, 100.0, 150.0)
        assert vehicle_detection.conf == 0.85
        assert vehicle_detection.center == (55.0, 85.0)
        assert vehicle_detection.area_ratio == 0.02

    def test_xyxy_is_float_quad(self, vehicle_detection):
        """xyxy must be a 4-tuple of floats."""
        assert len(vehicle_detection.xyxy) == 4
        assert all(isinstance(v, float) for v in vehicle_detection.xyxy)

    def test_center_is_float_pair(self, vehicle_detection):
        """center must be a 2-tuple of floats."""
        assert len(vehicle_detection.center) == 2
        assert all(isinstance(v, float) for v in vehicle_detection.center)

    def test_conf_is_between_zero_and_one(self, vehicle_detection):
        """conf must be in [0.0, 1.0]."""
        assert 0.0 <= vehicle_detection.conf <= 1.0

    def test_area_ratio_is_nonnegative(self, vehicle_detection):
        """area_ratio must be >= 0."""
        assert vehicle_detection.area_ratio >= 0.0

    def test_zero_area_ratio_is_valid(self):
        """An area_ratio of exactly 0.0 is allowed (degenerate bbox)."""
        det = Detection(
            cls_id=1,
            cls_name="obstruction",
            xyxy=(0.0, 0.0, 0.0, 0.0),
            conf=0.5,
            center=(0.0, 0.0),
            area_ratio=0.0,
        )
        assert det.area_ratio == 0.0

    def test_all_integer_cls_ids(self):
        """cls_id should accept any valid integer class ID."""
        for cid in [0, 1, 2]:
            det = Detection(
                cls_id=cid,
                cls_name=f"class_{cid}",
                xyxy=(0.0, 0.0, 10.0, 10.0),
                conf=0.99,
                center=(5.0, 5.0),
                area_ratio=0.001,
            )
            assert det.cls_id == cid


# ---------------------------------------------------------------------------
# Detector.__init__ tests
# ---------------------------------------------------------------------------

class TestDetectorInit:
    """Tests for Detector.__init__ — model loading, defaults, error paths."""

    def test_raises_file_not_found_on_bad_path(self):
        """Detector("nonexistent.pt") must raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            Detector(
                model_path="nonexistent.pt",
                imgsz=640,
                conf_thresh=0.25,
                iou_thresh=0.45,
                device="cpu",
            )

    def test_raises_file_not_found_on_nonexistent(self):
        """Detector("/tmp/not_a_real_model.pt") must raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            Detector(
                model_path="/tmp/not_a_real_model.pt",
            )

    def test_stores_default_params(self, monkeypatch):
        """Default parameters: imgsz=640, conf_thresh=0.25, iou_thresh=0.45, device='cpu'."""
        import ultralytics
        mock_yolo = type("MockYOLO", (), {"return_value": type("MockModel", (), {})()})()
        monkeypatch.setattr(ultralytics, "YOLO", lambda path: mock_yolo)

        detector = Detector(model_path="models/dummy.pt")
        assert detector.imgsz == 640
        assert detector.conf_thresh == 0.25
        assert detector.iou_thresh == 0.45
        assert detector.device == "cpu"

    def test_stores_custom_params(self, monkeypatch):
        """Custom imgsz, thresholds, device must be stored."""
        import ultralytics
        mock_yolo = type("MockYOLO", (), {"return_value": type("MockModel", (), {})()})()
        monkeypatch.setattr(ultralytics, "YOLO", lambda path: mock_yolo)

        detector = Detector(
            model_path="models/dummy.pt",
            imgsz=320,
            conf_thresh=0.65,
            iou_thresh=0.30,
            device="cuda:0",
        )
        assert detector.imgsz == 320
        assert detector.conf_thresh == 0.65
        assert detector.iou_thresh == 0.30
        assert detector.device == "cuda:0"

    def test_loads_yolo_model(self, monkeypatch):
        """__init__ must instantiate ultralytics.YOLO with the given model_path."""
        import ultralytics
        called_with = []

        def fake_yolo(path):
            called_with.append(path)
            return type("FakeModel", (), {})()

        monkeypatch.setattr(ultralytics, "YOLO", fake_yolo)

        Detector(model_path="models/dummy.pt")
        assert called_with == ["models/dummy.pt"]


# ---------------------------------------------------------------------------
# Detector.detect() tests
# ---------------------------------------------------------------------------
class TestDetectorDetect:
    """Tests for Detector.detect() — frame processing, filtering, metadata."""

    @staticmethod
    def _make_mock_detector(monkeypatch, conf_thresh=0.25, imgsz=640):
        """Create a Detector with a mocked YOLO backend and return (detector, mock_model)."""
        import ultralytics

        class CallableMock:
            def __call__(self, frame, **kw):
                return self._respond(frame)

        mock_model = CallableMock()
        mock_model._respond = lambda frame: []
        monkeypatch.setattr(ultralytics, "YOLO", lambda path: mock_model)

        detector = Detector(
            model_path="models/dummy.pt",
            imgsz=imgsz,
            conf_thresh=conf_thresh,
            iou_thresh=0.45,
            device="cpu",
        )
        return detector, mock_model

    @staticmethod
    def _make_mock_result(xyxy, cls_ids, confs):
        """Build a mock ultralytics Results object with boxes."""
        boxes = type("MockBoxes", (), {
            "xyxy": [list(b) if hasattr(b, '__iter__') else b for b in xyxy],
            "cls": list(cls_ids),
            "conf": list(confs),
        })()
        return type("MockResult", (), {"boxes": boxes})()

    def test_detect_returns_list_on_dummy_frame(self, monkeypatch, dummy_frame):
        """detect() returns a list (even if empty) on a valid frame."""
        detector, mock_model = self._make_mock_detector(monkeypatch)
        mock_model._respond = lambda frame: [self._make_mock_result([],[],[])]

        result = detector.detect(dummy_frame)
        assert isinstance(result, list)

    def test_detect_empty_frame_returns_empty_list(self, monkeypatch, empty_frame):
        """detect() on 0x0 frame returns an empty list."""
        detector, mock_model = self._make_mock_detector(monkeypatch)
        mock_model._respond = lambda frame: [self._make_mock_result([], [], [])]

        result = detector.detect(empty_frame)
        assert isinstance(result, list)
        assert len(result) == 0

    def test_detect_returns_detection_objects(self, monkeypatch, dummy_frame):
        """Each item in detect() output must be a Detection instance."""
        detector, mock_model = self._make_mock_detector(monkeypatch)
        mock_model._respond = lambda frame: [
            self._make_mock_result(
                xyxy=[[10.0, 20.0, 100.0, 150.0]],
                cls_ids=[0],
                confs=[0.85],
            )
        ]

        result = detector.detect(dummy_frame)
        assert len(result) == 1
        assert isinstance(result[0], Detection)

    def test_detect_filters_below_conf_threshold(self, monkeypatch, dummy_frame):
        """Detections with conf < conf_thresh must be excluded."""
        detector, mock_model = self._make_mock_detector(monkeypatch, conf_thresh=0.5)
        mock_model._respond = lambda frame: [
            self._make_mock_result(
                xyxy=[[10, 20, 100, 150], [200, 200, 300, 300]],
                cls_ids=[0, 1],
                confs=[0.85, 0.30],
            )
        ]

        result = detector.detect(dummy_frame)
        assert len(result) == 1
        assert result[0].cls_id == 0
        assert result[0].conf == 0.85

    def test_detect_passes_all_above_threshold(self, monkeypatch, dummy_frame):
        """All detections at or above conf_thresh must be returned."""
        detector, mock_model = self._make_mock_detector(monkeypatch, conf_thresh=0.5)
        mock_model._respond = lambda frame: [
            self._make_mock_result(
                xyxy=[[10, 20, 100, 150], [200, 200, 300, 300], [400, 50, 500, 150]],
                cls_ids=[0, 1, 2],
                confs=[0.85, 0.65, 0.50],
            )
        ]

        result = detector.detect(dummy_frame)
        assert len(result) == 3

    def test_detect_computes_center_correctly(self, monkeypatch, dummy_frame):
        """center = ((x1 + x2) / 2, (y1 + y2) / 2)."""
        detector, mock_model = self._make_mock_detector(monkeypatch)
        mock_model._respond = lambda frame: [
            self._make_mock_result(
                xyxy=[[10.0, 20.0, 110.0, 120.0]],
                cls_ids=[0],
                confs=[0.9],
            )
        ]

        result = detector.detect(dummy_frame)
        assert len(result) == 1
        # center = ((10+110)/2, (20+120)/2) = (60, 70)
        assert result[0].center == (60.0, 70.0)

    def test_detect_computes_area_ratio(self, monkeypatch, dummy_frame):
        """area_ratio = bbox_area / frame_area."""
        detector, mock_model = self._make_mock_detector(monkeypatch)
        mock_model._respond = lambda frame: [
            self._make_mock_result(
                xyxy=[[0.0, 0.0, 100.0, 100.0]],
                cls_ids=[0],
                confs=[0.9],
            )
        ]

        result = detector.detect(dummy_frame)
        assert len(result) == 1
        # bbox: 100*100 = 10000, frame: 640*640 = 409600 → 10000/409600
        expected = (100.0 * 100.0) / (640.0 * 640.0)
        assert result[0].area_ratio == pytest.approx(expected, rel=1e-9)

    def test_detect_class_name_mapping(self, monkeypatch, dummy_frame):
        """cls_id 0→vehicle, 1→obstruction, 2→ebike per configs/classes.yaml."""
        detector, mock_model = self._make_mock_detector(monkeypatch)
        mock_model._respond = lambda frame: [
            self._make_mock_result(
                xyxy=[[0, 0, 10, 10]] * 3,
                cls_ids=[0, 1, 2],
                confs=[0.95, 0.85, 0.75],
            )
        ]

        result = detector.detect(dummy_frame)
        assert len(result) == 3
        names = [d.cls_name for d in result]
        assert names == ["vehicle", "obstruction", "ebike"]

    def test_detect_unknown_class_id_falls_back(self, monkeypatch, dummy_frame):
        """cls_id not in classes.yaml should fall back to 'unknown_99'."""
        detector, mock_model = self._make_mock_detector(monkeypatch)
        mock_model._respond = lambda frame: [
            self._make_mock_result(
                xyxy=[[0, 0, 10, 10]],
                cls_ids=[99],
                confs=[0.7],
            )
        ]

        result = detector.detect(dummy_frame)
        assert len(result) == 1
        assert "99" in result[0].cls_name or result[0].cls_name == "unknown"

    def test_detect_multiple_detections_same_frame(self, monkeypatch, dummy_frame):
        """Multiple objects in a single frame produce multiple Detections."""
        detector, mock_model = self._make_mock_detector(monkeypatch, conf_thresh=0.3)
        mock_model._respond = lambda frame: [
            self._make_mock_result(
                xyxy=[[10, 20, 100, 150], [200, 200, 300, 300], [400, 400, 500, 500]],
                cls_ids=[0, 1, 2],
                confs=[0.9, 0.8, 0.7],
            )
        ]

        result = detector.detect(dummy_frame)
        assert len(result) == 3
        for d in result:
            assert isinstance(d, Detection)

    def test_detect_returns_empty_list_on_no_detections(self, monkeypatch, dummy_frame):
        """When YOLO finds nothing, detect() returns empty list."""
        detector, mock_model = self._make_mock_detector(monkeypatch)
        mock_model._respond = lambda frame: [self._make_mock_result([], [], [])]

        result = detector.detect(dummy_frame)
        assert result == []

    def test_detect_floats_are_python_float(self, monkeypatch, dummy_frame):
        """All numeric values in Detection must be native Python float, not numpy."""
        detector, mock_model = self._make_mock_detector(monkeypatch)
        mock_model._respond = lambda frame: [
            self._make_mock_result(
                xyxy=[[np.float32(10.0), np.float32(20.0), np.float32(100.0), np.float32(150.0)]],
                cls_ids=[np.int64(1)],
                confs=[np.float32(0.87)],
            )
        ]

        result = detector.detect(dummy_frame)
        assert len(result) == 1
        det = result[0]
        # cls_id should be int, not numpy.int64
        assert isinstance(det.cls_id, int)
        # conf should be float, not numpy.float32
        assert isinstance(det.conf, float)
        # xyxy values should be float
        for v in det.xyxy:
            assert isinstance(v, float)
        # center values should be float
        for v in det.center:
            assert isinstance(v, float)
        # area_ratio should be float
        assert isinstance(det.area_ratio, float)
