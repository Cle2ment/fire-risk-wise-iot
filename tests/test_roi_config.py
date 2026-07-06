"""RED tests for src/roi_config.py — must fail with ImportError before src/ exists."""

import pytest
from src.roi_config import ROIConfig

TEST_CONFIG = {
    "enabled": True,
    "zones": {
        "zone_a": {
            "polygon": [[0, 0], [100, 0], [100, 100], [0, 100]],
            "label": "Zone A",
        },
        "zone_b": {
            "polygon": [[200, 200], [300, 200], [300, 300], [200, 300]],
            "label": "Zone B",
        },
    },
}


class TestROIConfigInit:
    def test_load_from_dict(self):
        rc = ROIConfig(TEST_CONFIG)
        assert rc is not None

    def test_get_zone_labels(self):
        rc = ROIConfig(TEST_CONFIG)
        labels = rc.get_zone_labels()
        assert "Zone A" in labels
        assert "Zone B" in labels
        assert len(labels) == 2


class TestIsInsideAny:
    def test_inside_zone_a(self):
        rc = ROIConfig(TEST_CONFIG)
        assert rc.is_inside_any((50, 50)) is True

    def test_inside_zone_b(self):
        rc = ROIConfig(TEST_CONFIG)
        assert rc.is_inside_any((250, 250)) is True

    def test_outside_all(self):
        rc = ROIConfig(TEST_CONFIG)
        assert rc.is_inside_any((500, 500)) is False

    def test_on_boundary(self):
        rc = ROIConfig(TEST_CONFIG)
        assert rc.is_inside_any((0, 0)) is True


class TestIsInsideNamed:
    def test_named_zone_a_match(self):
        rc = ROIConfig(TEST_CONFIG)
        assert rc.is_inside("zone_a", (50, 50)) is True

    def test_named_zone_a_mismatch(self):
        rc = ROIConfig(TEST_CONFIG)
        assert rc.is_inside("zone_a", (250, 250)) is False

    def test_named_zone_b_match(self):
        rc = ROIConfig(TEST_CONFIG)
        assert rc.is_inside("zone_b", (250, 250)) is True

    def test_unknown_zone_name(self):
        rc = ROIConfig(TEST_CONFIG)
        assert rc.is_inside("nonexistent", (50, 50)) is False


class TestROIDisabled:
    def test_disabled_always_inside(self):
        cfg = {"enabled": False, "zones": {}}
        rc = ROIConfig(cfg)
        assert rc.is_inside_any((500, 500)) is True
        assert rc.is_inside_any((0, 0)) is True

    def test_empty_zones_enabled(self):
        cfg = {"enabled": True, "zones": {}}
        rc = ROIConfig(cfg)
        assert rc.is_inside_any((500, 500)) is True
