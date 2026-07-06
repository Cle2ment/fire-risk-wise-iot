#!/usr/bin/env python3
"""Fine-tune YOLOv8n on static.mp4 using COCO pseudo-labels mapped to fire-risk classes."""
import os
import shutil
import sys
from pathlib import Path

import cv2
from ultralytics import YOLO

ROOT = Path(__file__).resolve().parent.parent
VIDEO = ROOT / "demo" / "input" / "static.mp4"
DS = ROOT / "datasets" / "fire_risk"

# Import COCO→fire mapping from detector (single source of truth)
sys.path.insert(0, str(ROOT))
from src.detector import COCO_TO_FIRE  # noqa: E402


def extract_frames(video_path: Path, output_dir: Path, step: int = 2) -> list[Path]:
    """Extract every Nth frame from video (step=2 for denser sampling)."""
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
    """Generate YOLO-format pseudo-labels, mapping ALL detected COCO objects."""
    label_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    for fp in frames:
        results = base_model(str(fp), conf=0.15, verbose=False)
        labels: list[str] = []
        for r in results:
            if r.boxes is None:
                continue
            for box, cls_id in zip(r.boxes.xyxy, r.boxes.cls):
                cid = int(cls_id.item())
                fire_cls = COCO_TO_FIRE.get(cid, -1)
                if fire_cls < 0:
                    continue
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
    print(f"  Auto-labeled {count} frames with {sum(1 for p in label_dir.iterdir() if p.suffix=='.txt')} label files")
    return count


def split_train_val(frames: list[Path]):
    """Split frames into train (80%) and val (20%)."""
    import random
    random.seed(42)
    paths = sorted(frames)
    random.shuffle(paths)
    n_val = max(1, len(paths) // 5)
    val_set = {p.stem for p in paths[:n_val]}

    train_img = DS / "images" / "train"
    val_img = DS / "images" / "val"
    train_lbl = DS / "labels" / "train"
    val_lbl = DS / "labels" / "val"
    all_lbl = DS / "labels" / "labels_all"

    for fp in paths:
        stem = fp.stem
        lbl = all_lbl / f"{stem}.txt"
        if stem in val_set:
            shutil.copy2(fp, val_img / fp.name)
            if lbl.exists():
                shutil.copy2(lbl, val_lbl / f"{stem}.txt")
        else:
            shutil.copy2(fp, train_img / fp.name)
            if lbl.exists():
                shutil.copy2(lbl, train_lbl / f"{stem}.txt")

    n_train = len(list(train_img.glob("*.jpg")))
    n_val_count = len(list(val_img.glob("*.jpg")))
    print(f"  Split: {n_train} train, {n_val_count} val")


def main() -> None:
    print("=" * 60)
    print("Step 1: Extract frames (step=2, denser sampling)")
    print("=" * 60)
    for d in [DS / "images" / "train", DS / "images" / "val",
              DS / "labels" / "train", DS / "labels" / "val",
              DS / "images" / "all", DS / "labels" / "labels_all"]:
        d.mkdir(parents=True, exist_ok=True)
    frames = extract_frames(VIDEO, DS / "images" / "all", step=2)

    print()
    print("=" * 60)
    print("Step 2: Auto-label with full COCO→fire mapping (conf=0.15)")
    print("=" * 60)
    base = YOLO(str(ROOT / "models" / "yolov8n.pt"))
    auto_label(frames, DS / "labels" / "labels_all", base)

    print()
    print("=" * 60)
    print("Step 3: Train/val split (80/20)")
    print("=" * 60)
    split_train_val(frames)

    shutil.rmtree(DS / "images" / "all", ignore_errors=True)
    shutil.rmtree(DS / "labels" / "labels_all", ignore_errors=True)

    print()
    print("=" * 60)
    print("Step 4: Train YOLOv8n on fire-risk dataset (40 epochs)")
    print("=" * 60)

    model = YOLO(str(ROOT / "models" / "yolov8n.pt"))
    model.train(
        data=str(ROOT / "configs" / "dataset.yaml"),
        epochs=40,
        imgsz=640,
        batch=8,
        device="cpu",
        name="fire_risk",
        patience=15,
        exist_ok=True,
    )

    best = ROOT / "runs" / "detect" / "fire_risk" / "weights" / "best.pt"
    dst = ROOT / "models" / "fire_risk_best.pt"
    if best.is_file():
        shutil.copy2(best, dst)
        size_mb = os.path.getsize(dst) / 1e6
        print(f"\nBest model: {dst} ({size_mb:.1f} MB)")
    else:
        print("\nWARNING: best.pt not found, training may have failed")
        last = ROOT / "runs" / "detect" / "fire_risk" / "weights" / "last.pt"
        if last.is_file():
            shutil.copy2(last, dst)
            print(f"Fallback: using last.pt")

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
    print("Done. Run:")
    print("  uv run python src/main.py --model models/fire_risk_best.pt --input demo/input/static.mp4")


if __name__ == "__main__":
    main()
