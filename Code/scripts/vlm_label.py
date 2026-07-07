#!/usr/bin/env python3
"""VLM-assisted auto-labeling pipeline: extract frames → VLM annotate → YOLO format → train."""
import json
import os
import shutil
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parent.parent
VIDEO = ROOT / "demo" / "input" / "static.mp4"
DS = ROOT / "datasets" / "fire_risk"
CLASSES = ["vehicle","obstruction","ebike","debris_wood","debris_paper",
           "debris_mixed","congested_space","flammable_liquid","electrical_hazard"]
NAME2ID = {n: i for i, n in enumerate(CLASSES)}


def extract_keyframes(video: Path, out_dir: Path, step: int = 5) -> list[Path]:
    """Extract every Nth frame (step=5 → ~55 frames from 272)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(video))
    frames = []
    idx = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if idx % step == 0:
            path = out_dir / f"frame_{idx:05d}.jpg"
            cv2.imwrite(str(path), frame)
            frames.append(path)
        idx += 1
    cap.release()
    print(f"Extracted {len(frames)} keyframes (step={step})")
    return frames


def vlm_annotations_to_yolo(annotations_json: Path, frames: list[Path], label_dir: Path):
    """
    Convert VLM annotations JSON to YOLO format.
    
    Expected JSON format:
    {
      "frame_00000.jpg": [
        {"class": "debris_wood", "bbox": [x1, y1, x2, y2], "conf": 0.85},
        ...
      ],
      ...
    }
    """
    label_dir.mkdir(parents=True, exist_ok=True)
    
    with open(annotations_json) as f:
        data = json.load(f)
    
    count = 0
    for fp in frames:
        key = fp.name
        if key not in data:
            continue
        
        img = cv2.imread(str(fp))
        h, w = img.shape[:2]
        labels = []
        
        for ann in data[key]:
            cls_name = ann.get("class", "").lower()
            if cls_name not in NAME2ID:
                # Fuzzy match
                matched = None
                for cn in CLASSES:
                    if cn in cls_name or cls_name in cn:
                        matched = cn
                        break
                if not matched:
                    print(f"  WARNING: unknown class '{cls_name}' in {key}, skipping")
                    continue
                cls_name = matched
            
            cls_id = NAME2ID[cls_name]
            bbox = ann["bbox"]
            x1, y1, x2, y2 = float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])
            xc = ((x1 + x2) / 2.0) / w
            yc = ((y1 + y2) / 2.0) / h
            bw = (x2 - x1) / w
            bh = (y2 - y1) / h
            labels.append(f"{cls_id} {xc:.6f} {yc:.6f} {bw:.6f} {bh:.6f}")
        
        if labels:
            lbl_path = label_dir / f"{fp.stem}.txt"
            lbl_path.write_text("\n".join(labels))
            count += 1
    
    print(f"Converted {count} annotated frames to YOLO format")


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--annotations", help="Path to VLM annotations JSON", 
                   default=str(ROOT / "demo" / "output" / "vlm_annotations.json"))
    p.add_argument("--step", type=int, default=5, help="Frame extraction step")
    p.add_argument("--train", action="store_true", help="Run training after labeling")
    args = p.parse_args()
    
    print("=" * 60)
    print("Step 1: Extract keyframes")
    print("=" * 60)
    frames = extract_keyframes(VIDEO, DS / "images" / "all", step=args.step)
    
    ann_path = Path(args.annotations)
    if not ann_path.exists():
        print(f"\nERROR: Annotations file not found: {ann_path}")
        print("Run VLM annotation first, then provide the JSON file via --annotations")
        print(f"Example: put annotations in {ann_path}")
        return
    
    print()
    print("=" * 60)
    print("Step 2: Convert VLM annotations → YOLO format")
    print("=" * 60)
    vlm_annotations_to_yolo(ann_path, frames, DS / "labels" / "labels_all")
    
    # Split train/val
    import random
    random.seed(42)
    paths = sorted(frames)
    random.shuffle(paths)
    n_val = max(1, len(paths) // 5)
    val_set = {p.stem for p in paths[:n_val]}
    
    for fp in paths:
        stem = fp.stem
        src_img = fp
        src_lbl = DS / "labels" / "labels_all" / f"{stem}.txt"
        if stem in val_set:
            shutil.copy2(src_img, DS / "images" / "val" / fp.name)
            if src_lbl.exists():
                shutil.copy2(src_lbl, DS / "labels" / "val" / f"{stem}.txt")
        else:
            shutil.copy2(src_img, DS / "images" / "train" / fp.name)
            if src_lbl.exists():
                shutil.copy2(src_lbl, DS / "labels" / "train" / f"{stem}.txt")
    
    n_tr = len(list((DS / "images" / "train").glob("*.jpg")))
    n_vl = len(list((DS / "images" / "val").glob("*.jpg")))
    print(f"Split: {n_tr} train, {n_vl} val")
    
    shutil.rmtree(DS / "images" / "all", ignore_errors=True)
    shutil.rmtree(DS / "labels" / "labels_all", ignore_errors=True)
    
    if args.train:
        print()
        print("=" * 60)
        print("Step 3: Train YOLOv8n")
        print("=" * 60)
        from ultralytics import YOLO
        model = YOLO(str(ROOT / "models" / "yolov8n.pt"))
        model.train(
            data=str(ROOT / "configs" / "dataset.yaml"),
            epochs=50,
            imgsz=640,
            batch=8,
            device="cpu",
            name="fire_risk_vlm",
            patience=20,
            exist_ok=True,
        )
        best = ROOT / "runs" / "detect" / "fire_risk_vlm" / "weights" / "best.pt"
        if best.is_file():
            shutil.copy2(best, ROOT / "models" / "fire_risk_v3.pt")
            print(f"Model saved: models/fire_risk_v3.pt")
    else:
        print("\nData ready. Run with --train to start training:")
        print(f"  uv run python scripts/vlm_label.py --annotations {ann_path} --train")


if __name__ == "__main__":
    main()
