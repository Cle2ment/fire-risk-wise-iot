#!/usr/bin/env python3
"""Fine-tune YOLOv8 on fire risk detection dataset.

Dataset structure required:
    datasets/fire_risk/
    ├── images/
    │   ├── train/        # training images (.jpg/.png)
    │   └── val/          # validation images
    └── labels/
        ├── train/        # YOLO-format labels (.txt, one per image)
        └── val/

Label format (YOLO): <class_id> <x_center> <y_center> <width> <height>
All values normalized to [0, 1] relative to image dimensions.

Usage:
    uv run python scripts/train.py                          # default settings
    uv run python scripts/train.py --epochs 100 --imgsz 1280  # custom
    uv run python scripts/train.py --model yolov8s.pt       # use medium model
"""

import argparse
import sys
from pathlib import Path

from ultralytics import YOLO

ROOT = Path(__file__).resolve().parent.parent
DATASET_YAML = ROOT / "configs" / "dataset.yaml"
MODELS_DIR = ROOT / "models"
DATASET_ROOT = ROOT / "datasets" / "fire_risk"


def check_dataset() -> bool:
    """Validate dataset structure before training."""
    if not DATASET_YAML.is_file():
        print(f"ERROR: Dataset config not found: {DATASET_YAML}")
        return False

    for split in ("train", "val"):
        img_dir = DATASET_ROOT / "images" / split
        lbl_dir = DATASET_ROOT / "labels" / split
        if not img_dir.is_dir():
            print(f"ERROR: Missing {split} images: {img_dir}")
            print(f"  Create: mkdir -p {img_dir}")
            return False
        if not lbl_dir.is_dir():
            print(f"ERROR: Missing {split} labels: {lbl_dir}")
            print(f"  Create: mkdir -p {lbl_dir}")
            return False

        imgs = list(img_dir.glob("*.jpg")) + list(img_dir.glob("*.png"))
        lbls = list(lbl_dir.glob("*.txt"))
        print(f"  {split}: {len(imgs)} images, {len(lbls)} labels")

        if len(imgs) == 0:
            print(f"  WARNING: No images in {split} set")
        if len(lbls) == 0:
            print(f"  WARNING: No labels in {split} set")

    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Fine-tune YOLOv8 for fire risk detection")
    parser.add_argument("--model", default="yolov8n.pt", help="Base model (default: yolov8n.pt)")
    parser.add_argument("--epochs", type=int, default=50, help="Training epochs (default: 50)")
    parser.add_argument("--imgsz", type=int, default=640, help="Image size (default: 640)")
    parser.add_argument("--batch", type=int, default=16, help="Batch size (default: 16)")
    parser.add_argument("--device", default="cpu", help="Device (default: cpu)")
    parser.add_argument("--name", default="fire_risk", help="Run name")
    parser.add_argument("--patience", type=int, default=10, help="Early stopping patience")
    parser.add_argument("--dry-run", action="store_true", help="Only check dataset, don't train")
    args = parser.parse_args()

    print("=" * 60)
    print("Fire Risk Detection — YOLOv8 Fine-Tuning")
    print("=" * 60)

    if not check_dataset():
        print()
        print("--- Dataset Preparation Guide ---")
        print()
        print("1. Create directory structure:")
        print(f"   mkdir -p {DATASET_ROOT}/images/train")
        print(f"   mkdir -p {DATASET_ROOT}/images/val")
        print(f"   mkdir -p {DATASET_ROOT}/labels/train")
        print(f"   mkdir -p {DATASET_ROOT}/labels/val")
        print()
        print("2. Add images to images/train/ and images/val/")
        print("3. Annotate with any YOLO-compatible tool:")
        print("   - LabelImg: https://github.com/HumanSignal/labelImg")
        print("   - Label Studio: https://labelstud.io/")
        print("   - Roboflow: https://roboflow.com/")
        print("   - CVAT: https://www.cvat.ai/")
        print(f"4. Place .txt labels in {DATASET_ROOT}/labels/train/ and val/")
        print(f"   9 classes: vehicle, obstruction, ebike, debris_wood,")
        print(f"              debris_paper, debris_mixed, congested_space,")
        print(f"              flammable_liquid, electrical_hazard")
        sys.exit(1)

    if args.dry_run:
        print("Dataset check passed. Ready for training.")
        return

    # Base model: download if needed, or use existing
    base_model = args.model
    if not Path(base_model).is_file():
        # Check models/ directory
        local = MODELS_DIR / base_model
        if local.is_file():
            base_model = str(local)
        else:
            print(f"Downloading base model: {args.model}")

    model = YOLO(base_model)

    print(f"\nTraining configuration:")
    print(f"  Base model: {base_model}")
    print(f"  Dataset:    {DATASET_YAML}")
    print(f"  Epochs:     {args.epochs}")
    print(f"  Image size: {args.imgsz}")
    print(f"  Batch size: {args.batch}")
    print(f"  Device:     {args.device}")
    print(f"  Name:       {args.name}")
    print()

    results = model.train(
        data=str(DATASET_YAML),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        name=args.name,
        patience=args.patience,
        exist_ok=True,
    )

    # Copy best model to models/
    best = ROOT / "runs" / "detect" / args.name / "weights" / "best.pt"
    if best.is_file():
        dst = MODELS_DIR / "fire_risk_best.pt"
        import shutil
        shutil.copy2(best, dst)
        print(f"\nBest model saved to: {dst}")

    print("\nTraining complete. Use with:")
    print(f"  uv run python src/main.py --model models/fire_risk_best.pt --input demo/input/static.mp4")


if __name__ == "__main__":
    main()
