#!/usr/bin/env python3
"""End-to-end fine-tuning pipeline: extract frames, auto-label, train, deploy."""
import os, shutil, sys
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO

ROOT = Path(__file__).resolve().parent.parent
VIDEO = ROOT / "demo" / "input" / "static.mp4"
DS = ROOT / "datasets" / "fire_risk"

# COCO class → our fire-risk class mapping (only relevant classes)
COCO_TO_FIRE: dict[int, int] = {
    2: 0,   # car → vehicle
    3: 0,   # motorcycle → vehicle
    5: 0,   # bus → vehicle
    7: 0,   # truck → vehicle
    56: 6,  # chair → congested_space (furniture blocking)
    57: 6,  # couch → congested_space
    59: 6,  # bed → congested_space
    60: 6,  # dining table → congested_space
    61: 6,  # toilet → congested_space
    62: 3,  # tv → debris_mixed (electronics clutter)
    63: 4,  # laptop → debris_mixed
    64: 4,  # mouse → debris_mixed
    65: 4,  # remote → debris_mixed
    66: 4,  # keyboard → debris_mixed
    67: 4,  # cell phone → debris_mixed
    68: 3,  # microwave → debris_mixed
    69: 3,  # oven → debris_mixed
    70: 3,  # toaster → debris_mixed
    71: 3,  # sink → debris_mixed
    72: 4,  # refrigerator → debris_mixed
    73: 4,  # book → debris_paper
    74: 3,  # clock → debris_mixed
    75: 4,  # vase → debris_mixed
    76: 4,  # scissors → debris_mixed
    77: 4,  # teddy bear → debris_mixed
    78: 4,  # hair drier → electrical_hazard
    79: 4,  # toothbrush → debris_mixed
    84: 4,  # book → debris_paper
}


def extract_frames(video_path: Path, output_dir: Path, step: int = 5) -> list[Path]:
    """Extract every Nth frame from video."""
    output_dir.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(video_path))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frames: list[Path] = []
    idx = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if idx % step == 0:
            path = output_dir / f"frame_{idx:05d}.jpg"
            cv2.imwrite(str(path), frame)
            frames.append(path)
        idx += 1
    cap.release()
    print(f"  Extracted {len(frames)} frames from {total} total (step={step})")
    return frames


def auto_label(frames: list[Path], label_dir: Path, base_model: YOLO) -> int:
    """Generate YOLO-format pseudo-labels using the base COCO model."""
    label_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    for fp in frames:
        results = base_model(str(fp), conf=0.25, verbose=False)
        labels: list[str] = []
        for r in results:
            if r.boxes is None:
                continue
            for box, cls_id, conf in zip(r.boxes.xyxy, r.boxes.cls, r.boxes.conf):
                cid = int(cls_id.item())
                if cid not in COCO_TO_FIRE:
                    continue
                fire_cls = COCO_TO_FIRE[cid]
                x1, y1, x2, y2 = box.tolist()
                h_img, w_img = r.orig_shape
                xc = (x1 + x2) / 2.0 / w_img
                yc = (y1 + y2) / 2.0 / h_img
                bw = (x2 - x1) / w_img
                bh = (y2 - y1) / h_img
                labels.append(f"{fire_cls} {xc:.6f} {yc:.6f} {bw:.6f} {bh:.6f}")
        if labels:
            lbl_path = label_dir / f"{fp.stem}.txt"
            lbl_path.write_text("\n".join(labels))
            count += 1
    print(f"  Auto-labeled {count} frames → {label_dir}")
    return count


def split_train_val(frames: list[Path], all_frames_dir: Path):
    """Split frames into train (80%) and val (20%), copying images."""
    import random
    random.seed(42)
    paths = sorted(frames)
    random.shuffle(paths)
    n_val = max(1, len(paths) // 5)
    val_set = set(p.stem for p in paths[:n_val])

    train_img = DS / "images" / "train"
    val_img = DS / "images" / "val"
    train_lbl = DS / "labels" / "train"
    val_lbl = DS / "labels" / "val"

    all_lbl = DS / "labels" / "labels_all"

    for fp in paths:
        stem = fp.stem
        src_img = fp
        src_lbl = all_lbl / f"{stem}.txt"
        if stem in val_set:
            shutil.copy2(src_img, val_img / fp.name)
            if src_lbl.exists():
                shutil.copy2(src_lbl, val_lbl / f"{stem}.txt")
        else:
            shutil.copy2(src_img, train_img / fp.name)
            if src_lbl.exists():
                shutil.copy2(src_lbl, train_lbl / f"{stem}.txt")

    n_train = len(list(train_img.glob("*.jpg")))
    n_val = len(list(val_img.glob("*.jpg")))
    print(f"  Split: {n_train} train, {n_val} val")


def main() -> None:
    print("=" * 60)
    print("Step 1: Extract frames from video")
    print("=" * 60)
    frames_dir = DS / "images" / "all"
    frames = extract_frames(VIDEO, frames_dir, step=3)

    print()
    print("=" * 60)
    print("Step 2: Auto-label with COCO YOLOv8n")
    print("=" * 60)
    base = YOLO(str(ROOT / "models" / "yolov8n.pt"))
    auto_label(frames, DS / "labels" / "labels_all", base)

    print()
    print("=" * 60)
    print("Step 3: Train/val split (80/20)")
    print("=" * 60)
    split_train_val(frames, frames_dir)

    # Cleanup intermediate files
    shutil.rmtree(DS / "images" / "all", ignore_errors=True)
    shutil.rmtree(DS / "labels" / "labels_all", ignore_errors=True)

    print()
    print("=" * 60)
    print("Step 4: Train YOLOv8n on fire-risk dataset")
    print("=" * 60)

    model = YOLO(str(ROOT / "models" / "yolov8n.pt"))
    results = model.train(
        data=str(ROOT / "configs" / "dataset.yaml"),
        epochs=30,
        imgsz=640,
        batch=8,
        device="cpu",
        name="fire_risk",
        patience=10,
        exist_ok=True,
    )

    # Copy best model
    best = ROOT / "runs" / "detect" / "fire_risk" / "weights" / "best.pt"
    dst = ROOT / "models" / "fire_risk_best.pt"
    if best.is_file():
        shutil.copy2(best, dst)
        print(f"\nBest model: {dst} ({os.path.getsize(dst) / 1e6:.1f} MB)")

    print()
    print("=" * 60)
    print("Step 5: Run inference with fine-tuned model")
    print("=" * 60)

    fine_model = YOLO(str(dst))
    results2 = fine_model(str(VIDEO), stream=True, verbose=False)

    frame_count = 0
    det_count = 0
    classes_seen: set[str] = set()
    for r in results2:
        frame_count += 1
        if r.boxes is not None and len(r.boxes) > 0:
            det_count += len(r.boxes)
            for cid in r.boxes.cls:
                classes_seen.add(r.names[int(cid)])

    print(f"  Frames processed: {frame_count}")
    print(f"  Total detections: {det_count}")
    print(f"  Classes detected: {sorted(classes_seen)}")
    print()
    print("Done. Fine-tuned model ready:")
    print(f"  uv run python src/main.py --model models/fire_risk_best.pt --input demo/input/static.mp4")


if __name__ == "__main__":
    main()
