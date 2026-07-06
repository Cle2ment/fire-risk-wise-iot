"""RED-phase tests for src/utils.py — must fail with ImportError before src/ exists."""

import pytest
import time
import json
import os
import tempfile
import logging

from src.utils import FPSTimer, risk_level_color, get_gradient_color, setup_logger, generate_report


# ---------------------------------------------------------------------------
# FPSTimer
# ---------------------------------------------------------------------------
class TestFPSTimer:
    def test_fps_timer_tick_returns_float(self):
        """create timer, tick several times with sleep, verify returns float > 0"""
        timer = FPSTimer()
        time.sleep(0.05)
        fps = timer.tick()
        assert isinstance(fps, float)
        assert fps >= 0

    def test_fps_timer_elapsed_increases(self):
        """verify elapsed() grows over time"""
        timer = FPSTimer()
        t0 = timer.elapsed()
        time.sleep(0.1)
        t1 = timer.elapsed()
        assert t1 > t0

    def test_fps_timer_elapsed_returns_float(self):
        """verify elapsed() returns a float"""
        timer = FPSTimer()
        assert isinstance(timer.elapsed(), float)

    def test_fps_timer_frame_count(self):
        """verify frame_count increments with each tick()"""
        timer = FPSTimer()
        assert timer.frame_count() == 0
        timer.tick()
        assert timer.frame_count() == 1
        timer.tick()
        assert timer.frame_count() == 2


# ---------------------------------------------------------------------------
# risk_level_color
# ---------------------------------------------------------------------------
class TestRiskLevelColor:
    def test_risk_level_color_low(self):
        """returns green BGR tuple"""
        assert risk_level_color("low") == (0, 255, 0)

    def test_risk_level_color_medium(self):
        """returns yellow BGR tuple"""
        assert risk_level_color("medium") == (0, 255, 255)

    def test_risk_level_color_high(self):
        """returns red BGR tuple"""
        assert risk_level_color("high") == (0, 0, 255)

    def test_risk_level_color_invalid(self):
        """raises ValueError for unknown level"""
        with pytest.raises(ValueError):
            risk_level_color("critical")


# ---------------------------------------------------------------------------
# get_gradient_color — returns (R, G, B)
# ---------------------------------------------------------------------------
class TestGetGradientColor:
    def test_get_gradient_color_zero(self):
        """score 0 returns green (0, 255, 0)"""
        b, g, r = get_gradient_color(0.0)
        assert g > 200
        assert r < 50
        assert b < 50

    def test_get_gradient_color_fifty(self):
        """score 50 returns yellow (255, 255, 0)"""
        b, g, r = get_gradient_color(50.0)
        assert g > 200
        assert r > 200
        assert b < 50

    def test_get_gradient_color_hundred(self):
        """score 100 returns red (255, 0, 0)"""
        b, g, r = get_gradient_color(100.0)
        assert r > 200
        assert g < 50
        assert b < 50

    def test_get_gradient_color_midpoint(self):
        """score 25 returns green->yellow mix"""
        b, g, r = get_gradient_color(25.0)
        assert g > 100
        assert 50 <= r <= 200

    def test_get_gradient_color_clamp(self):
        """scores <0 and >100 are clamped"""
        b0, g0, r0 = get_gradient_color(-10.0)
        assert g0 > 200 and b0 < 50  # clamped to 0 (green)

        b1, g1, r1 = get_gradient_color(150.0)
        assert r1 > 200 and g1 < 50  # clamped to 100 (red)


# ---------------------------------------------------------------------------
# setup_logger
# ---------------------------------------------------------------------------
class TestSetupLogger:
    @pytest.fixture(autouse=True)
    def temp_log_path(self) -> str:
        """Create a temporary log path and clean up after."""
        fd, path = tempfile.mkstemp(suffix=".log", prefix="test_utils_")
        os.close(fd)
        os.remove(path)  # remove so setup_logger creates it fresh
        yield path
        if os.path.exists(path):
            os.remove(path)

    def test_setup_logger_returns_logger(self, temp_log_path: str) -> None:
        """returns logging.Logger instance"""
        logger = setup_logger(temp_log_path)
        assert isinstance(logger, logging.Logger)

    def test_setup_logger_creates_file(self, temp_log_path: str) -> None:
        """log file is created at log_path"""
        _logger = setup_logger(temp_log_path)
        assert os.path.exists(temp_log_path)


# ---------------------------------------------------------------------------
# generate_report
# ---------------------------------------------------------------------------
class TestGenerateReport:
    def _sample_frames(self) -> list[dict]:
        return [
            {"frame": 0, "score": 0.0, "level": "low", "active_risks": []},
            {"frame": 1, "score": 45.0, "level": "medium", "active_risks": ["obstruction"]},
        ]

    def _sample_metadata(self) -> dict:
        return {"input": "test.mp4", "fps": 30.0}

    def test_generate_report_output_path(self) -> None:
        """creates JSON file at output_path"""
        frame_results = self._sample_frames()
        metadata = self._sample_metadata()
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = os.path.join(tmpdir, "report.json")
            generate_report(frame_results, metadata, out_path)
            assert os.path.exists(out_path)

    def test_generate_report_structure(self) -> None:
        """returns dict with metadata, summary, frame_details keys"""
        frame_results = self._sample_frames()
        metadata = self._sample_metadata()
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = os.path.join(tmpdir, "report.json")
            result = generate_report(frame_results, metadata, out_path)
            assert isinstance(result, dict)
            assert "metadata" in result
            assert "summary" in result
            assert "frame_details" in result
            assert result["metadata"]["input"] == "test.mp4"

