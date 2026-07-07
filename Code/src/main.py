#!/usr/bin/env python3
"""Main pipeline: load configs, process video, produce annotated output + JSON report."""
import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np
import yaml

from src.detector import Detector
from src.risk_engine import RiskEngine
from src.roi_config import ROIConfig
from src.utils import FPSTimer, generate_report
from src.visualizer import Visualizer


def load_config(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def main() -> None:
    p = argparse.ArgumentParser(description="Fire Risk Detection Probe — inference pipeline")
    p.add_argument("--input", required=True, help="Path to input video file")
    p.add_argument("--output", default="demo/output/annotated.mp4", help="Path to output video file")
    p.add_argument("--config", default="configs/default.yaml", help="Path to YAML config file")
    p.add_argument("--model", default=None, help="Override model path in config")
    p.add_argument("--device", default=None, help="Override device in config")
    p.add_argument("--roi-debug", action="store_true", help="Draw ROI polygons on output")
    args = p.parse_args()

    # --- load configs ---
    cfg = load_config(args.config)
    model_path = args.model or cfg["inference"]["model_path"]
    device = args.device or cfg["inference"]["device"]

    # --- open video ---
    cap = cv2.VideoCapture(args.input)
    if not cap.isOpened():
        print(f"ERROR: cannot open video: {args.input}", file=sys.stderr)
        sys.exit(1)

    fps_src = cap.get(cv2.CAP_PROP_FPS)
    fps_out = cfg["output"].get("video_fps") or fps_src or 25.0
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(out_path), fourcc, fps_out, (w, h))

    # --- pipeline components ---
    det_cfg = cfg["inference"]
    detector = Detector(
        model_path=model_path,
        imgsz=det_cfg.get("imgsz", 640),
        conf_thresh=det_cfg.get("conf_threshold", 0.25),
        iou_thresh=det_cfg.get("iou_threshold", 0.45),
        device=device,
    )

    roi = ROIConfig(cfg.get("roi", {}))
    risk = RiskEngine(
        classes_config=load_config("configs/classes.yaml"),
        roi_config=roi,
        score_history_window=cfg.get("risk", {}).get("score_history_window", 30),
        alert_cooldown_sec=cfg.get("risk", {}).get("alert_cooldown_sec", 5.0),
        min_detection_area_ratio=cfg.get("risk", {}).get("min_detection_area_ratio", 0.001),
    )

    vis = Visualizer()
    timer = FPSTimer()
    frame_results: list[dict] = []
    frame_idx = 0

    print(f"Processing: {args.input}  →  {args.output}")
    print(f"  model={model_path}  device={device}  {w}x{h}@{fps_src:.1f}fps")

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        timestamp = frame_idx / fps_src if fps_src > 0 else float(frame_idx)

        # --- pipeline ---
        detections = detector.detect(frame)
        frame_risk = risk.evaluate(frame_idx, detections, timestamp)
        annotated = vis.draw(frame, detections, frame_risk, timer.tick())

        # ROI debug overlay
        if args.roi_debug:
            for zname, zone in roi._zones.items():
                pts = np.array(zone["polygon"], np.int32).reshape((-1, 1, 2))
                cv2.polylines(annotated, [pts], True, (0, 255, 255), 2)
                cv2.putText(annotated, zname, tuple(pts[0, 0]),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

        writer.write(annotated)

        frame_results.append({
            "frame": frame_idx,
            "timestamp_sec": round(timestamp, 3),
            "score": round(frame_risk.score, 2),
            "level": frame_risk.level,
            "active_risks": [
                {"type": evt.risk_type, "score": round(evt.score, 2), "level": evt.level, "zone": evt.zone}
                for evt in frame_risk.active_risks
            ],
        })

        frame_idx += 1
        if frame_idx % 100 == 0:
            print(f"  frame {frame_idx}  score={frame_risk.score:.1f}  level={frame_risk.level}")

    cap.release()
    writer.release()

    # --- report ---
    report_path = out_path.with_suffix(".json")
    generate_report(
        frame_results,
        {
            "input": args.input,
            "output": str(out_path),
            "model": model_path,
            "device": device,
            "total_frames": frame_idx,
            "source_fps": fps_src,
        },
        str(report_path),
    )

    print(f"\nDone.  {frame_idx} frames  →  {out_path}")
    print(f"Report  →  {report_path}")


if __name__ == "__main__":
    main()
