#!/usr/bin/env python3
"""VLM auto-labeling via CherryIn API → YOLO format → train."""
import argparse, base64, json, os, shutil, time
from pathlib import Path
import cv2
from openai import OpenAI

ROOT = Path(__file__).resolve().parent.parent
VIDEO = ROOT / "demo" / "input" / "static.mp4"
DS = ROOT / "datasets" / "fire_risk"
CLASSES = ["vehicle","obstruction","ebike","debris_wood","debris_paper",
           "debris_mixed","congested_space","flammable_liquid","electrical_hazard"]
NAME2ID = {n: i for i, n in enumerate(CLASSES)}

def _parse_json(text: str) -> dict:
    """Robust JSON extraction from VLM response."""
    text = text.strip()
    for pfx in ["```json\n", "```json", "```\n", "```"]:
        if text.startswith(pfx):
            text = text[len(pfx):]
    for sfx in ["\n```", "```"]:
        if text.endswith(sfx):
            text = text[:-len(sfx)]
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    s = text.find("{")
    e = text.rfind("}")
    if s >= 0 and e > s:
        try:
            return json.loads(text[s:e + 1])
        except json.JSONDecodeError:
            pass
    return {"objects": []}

def call_vlm(client: OpenAI, model: str, img_path: Path, h: int, w: int) -> dict:
    with open(img_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    prompt = (
        f"You are analyzing a security camera frame ({w}x{h}px) for fire safety hazards in a building. "
        "List every object that poses a fire risk. Return ONLY a JSON object, nothing else.\n\n"
        '{"objects":[{"class":"debris_wood","bbox":[100,200,400,500],"conf":0.9}]}\n\n'
        "Valid classes: vehicle, obstruction, ebike, debris_wood, debris_paper, debris_mixed, "
        "congested_space, flammable_liquid, electrical_hazard.\n"
        "bbox is [x1,y1,x2,y2] pixel coordinates. conf is 0-1.\n"
        'If no hazards: {"objects":[]}\n\n'
        "DO NOT add explanations. ONLY JSON."
    )
    for attempt in range(3):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role":"user","content":[
                    {"type":"text","text":prompt},
                    {"type":"image_url","image_url":{"url":f"data:image/jpeg;base64,{b64}","detail":"high"}},
                ]}],
                temperature=0.0, max_tokens=4096)
            return _parse_json(resp.choices[0].message.content or "")
        except Exception as e:
            if attempt < 2:
                time.sleep(3)
                continue
            print(f"  FAILED: {e}")
            return {"objects": []}
    return {"objects": []}

def extract_frames(video: Path, out: Path, step: int) -> list[Path]:
    out.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(video))
    frames, idx = [], 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if idx % step == 0:
            path = out / f"frame_{idx:05d}.jpg"
            cv2.imwrite(str(path), frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
            frames.append(path)
        idx += 1
    cap.release()
    return frames

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--api-key", default=os.environ.get("CHERRYIN_API_KEY",""))
    p.add_argument("--base-url", default="https://open.cherryin.ai/v1")
    p.add_argument("--model", default="google/gemini-2.5-flash")
    p.add_argument("--step", type=int, default=5)
    p.add_argument("--train", action="store_true")
    args = p.parse_args()

    if not args.api_key:
        print("ERROR: set CHERRYIN_API_KEY"); return

    client = OpenAI(api_key=args.api_key, base_url=args.base_url)
    print(f"Connected. Model: {args.model}")

    print("Step 1: Extract keyframes ...")
    frames = extract_frames(VIDEO, DS / "images" / "all", step=args.step)
    print(f"  {len(frames)} frames (step={args.step})")

    print(f"\nStep 2: VLM annotation ({args.model})")
    annotations = {}
    for i, fp in enumerate(frames):
        img = cv2.imread(str(fp))
        h, w = img.shape[:2]
        print(f"  [{i+1}/{len(frames)}] {fp.name} ...", end=" ", flush=True)
        result = call_vlm(client, args.model, fp, h, w)
        n = len(result.get("objects", []))
        classes_found = {o["class"] for o in result.get("objects", [])}
        print(f"{n} hazards: {sorted(classes_found)}" if n else "no hazards")
        annotations[fp.name] = result
        time.sleep(0.3)

    ann_path = ROOT / "demo" / "output" / "vlm_annotations.json"
    ann_path.parent.mkdir(parents=True, exist_ok=True)
    with open(ann_path, "w") as f:
        json.dump(annotations, f, indent=2, ensure_ascii=False)
    total = sum(len(v.get("objects",[])) for v in annotations.values())
    print(f"\n  Total: {total} hazards → {ann_path}")

    print("\nStep 3: Convert to YOLO format ...")
    lbl_dir = DS / "labels" / "labels_all"
    lbl_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    for fp in frames:
        key = fp.name
        if key not in annotations:
            continue
        objs = annotations[key].get("objects", [])
        if not objs:
            continue
        img = cv2.imread(str(fp))
        h, w = img.shape[:2]
        labels = []
        for obj in objs:
            cn = obj["class"].lower().replace(" ","_")
            if cn not in NAME2ID:
                for c in CLASSES:
                    if c in cn or cn in c:
                        cn = c; break
                else:
                    continue
            cid = NAME2ID[cn]
            x1,y1,x2,y2 = [float(v) for v in obj["bbox"]]
            labels.append(f"{cid} {(x1+x2)/2/w:.6f} {(y1+y2)/2/h:.6f} {(x2-x1)/w:.6f} {(y2-y1)/h:.6f}")
        if labels:
            (lbl_dir / f"{fp.stem}.txt").write_text("\n".join(labels))
            count += 1
    print(f"  {count} frames with labels")

    # train/val split
    import random; random.seed(42)
    paths = sorted(frames); random.shuffle(paths)
    nv = max(1, len(paths)//5)
    vs = {p.stem for p in paths[:nv]}
    for fp in paths:
        s = fp.stem
        tgt_img = "val" if s in vs else "train"
        shutil.copy2(fp, DS / "images" / tgt_img / fp.name)
        lbl = lbl_dir / f"{s}.txt"
        if lbl.exists():
            shutil.copy2(lbl, DS / "labels" / tgt_img / f"{s}.txt")
    nt = len(list((DS/"images"/"train").glob("*.jpg")))
    nv2 = len(list((DS/"images"/"val").glob("*.jpg")))
    print(f"  Split: {nt} train / {nv2} val")
    shutil.rmtree(DS/"images"/"all", ignore_errors=True)
    shutil.rmtree(lbl_dir, ignore_errors=True)

    if args.train:
        print("\nStep 4: Train YOLOv8n ...")
        from ultralytics import YOLO
        model = YOLO(str(ROOT / "models" / "yolov8n.pt"))
        model.train(data=str(ROOT / "configs" / "dataset.yaml"), epochs=50, imgsz=640,
                    batch=8, device="cpu", name="fire_risk_vlm", patience=20, exist_ok=True)
        best = ROOT / "runs" / "detect" / "fire_risk_vlm" / "weights" / "best.pt"
        if best.is_file():
            shutil.copy2(best, ROOT / "models" / "fire_risk_v3.pt")
            print(f"  Model: models/fire_risk_v3.pt ({os.path.getsize(best)/1e6:.1f}MB)")
    else:
        print(f"\nDone. To train: uv run python scripts/vlm_autolabel.py --train")

if __name__ == "__main__":
    main()
