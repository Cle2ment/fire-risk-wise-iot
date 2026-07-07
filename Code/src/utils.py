"""Utility functions: FPS timer, color mapping, logging, report generation."""

import json
import logging
import os
import time
from typing import Any


class FPSTimer:
    """Track frame processing time and compute FPS."""

    def __init__(self) -> None:
        self._start = time.perf_counter()
        self._last_tick = self._start
        self._frames = 0

    def tick(self) -> float:
        """Mark a new frame processed and return current FPS."""
        self._frames += 1
        now = time.perf_counter()
        elapsed = now - self._last_tick
        self._last_tick = now
        return 1.0 / elapsed if elapsed > 0 else 0.0

    def elapsed(self) -> float:
        """Return total elapsed seconds since timer creation."""
        return time.perf_counter() - self._start

    def frame_count(self) -> int:
        """Return total frames processed."""
        return self._frames


def risk_level_color(level: str) -> tuple[int, int, int]:
    """Return BGR color tuple for a risk level string."""
    if level == "low":
        return (0, 255, 0)
    elif level == "medium":
        return (0, 255, 255)
    elif level == "high":
        return (0, 0, 255)
    raise ValueError(f"Unknown risk level: {level}")


def _lerp_rgb(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    """Linearly interpolate between two RGB tuples."""
    t = max(0.0, min(1.0, t))
    return (
        int(a[0] + (b[0] - a[0]) * t),
        int(a[1] + (b[1] - a[1]) * t),
        int(a[2] + (b[2] - a[2]) * t),
    )


def get_gradient_color(score: float) -> tuple[int, int, int]:
    """Map score 0→green, 50→yellow, 100→red via linear BGR interpolation.

    Returns (B, G, R) tuple. Clamps score to [0, 100].
    """
    score = max(0.0, min(100.0, float(score)))
    green_bgr = (0, 255, 0)
    yellow_bgr = (0, 255, 255)
    red_bgr = (0, 0, 255)

    if score <= 50.0:
        return _lerp_rgb(green_bgr, yellow_bgr, score / 50.0)
    else:
        return _lerp_rgb(yellow_bgr, red_bgr, (score - 50.0) / 50.0)


def setup_logger(log_path: str) -> logging.Logger:
    """Create and return a file logger at log_path."""
    logger = logging.getLogger(log_path)
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    os.makedirs(os.path.dirname(log_path) or ".", exist_ok=True)
    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(handler)
    return logger


def generate_report(
    frame_results: list[dict[str, Any]],
    metadata: dict[str, Any],
    output_path: str,
) -> dict[str, Any]:
    """Write a JSON report and return its contents as a dict."""
    total = len(frame_results)
    scores = [fr.get("score", 0.0) for fr in frame_results]
    high_count = sum(1 for fr in frame_results if fr.get("level") == "high")
    medium_count = sum(1 for fr in frame_results if fr.get("level") == "medium")
    peak_score = max(scores) if scores else 0.0
    avg_score = sum(scores) / total if total > 0 else 0.0

    report: dict[str, Any] = {
        "metadata": metadata,
        "summary": {
            "total_frames": total,
            "peak_score": round(peak_score, 2),
            "average_score": round(avg_score, 2),
            "high_risk_frames": high_count,
            "medium_risk_frames": medium_count,
        },
        "frame_details": frame_results,
    }

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    return report
