"""DINOv2 features of the boss crops of a recording (boss_track.py), one row per crop.

Usage: python -I boss_features.py <recording id | all> [--model vit_small_patch14_dinov2.lvd142m]

Each crop is resized to 224×224 and goes through the pretrained model (timm, fp16 on the GPU). A row is the class token
followed by the mean of the patch tokens, L2-normalised separately, so either half can be used alone. Writes
work/<recording id>/boss_feats_<short model name>.npy (float16, rows in boss_track.csv order).
"""
import sys
from pathlib import Path

import numpy as np
import timm
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from boss_track import load_crops  # noqa: E402
from common import recordings, work_dir  # noqa: E402

MODEL = "vit_small_patch14_dinov2.lvd142m"
MEAN, STD = (0.485, 0.456, 0.406), (0.229, 0.224, 0.225)


def short(name):
    return name.split(".")[0].replace("vit_", "").replace("_patch14_dinov2", "14")


def features(rec_id, name, batch=128):
    model = timm.create_model(name, pretrained=True, num_classes=0, img_size=224).eval().cuda().half()
    crops = load_crops(rec_id)                         # BGR uint8
    mean = torch.tensor(MEAN, device="cuda").view(1, 3, 1, 1)
    std = torch.tensor(STD, device="cuda").view(1, 3, 1, 1)
    out = []
    with torch.no_grad():
        for i in range(0, len(crops), batch):
            x = torch.from_numpy(crops[i:i + batch][..., ::-1].copy()).cuda().permute(0, 3, 1, 2).float() / 255
            x = torch.nn.functional.interpolate(x, size=(224, 224), mode="bilinear", antialias=True, align_corners=False)
            tokens = model.forward_features(((x - mean) / std).half()).float()
            cls, patch = tokens[:, 0], tokens[:, 1:].mean(1)
            out.append(torch.cat([torch.nn.functional.normalize(cls, dim=1),
                                  torch.nn.functional.normalize(patch, dim=1)], 1).cpu().numpy().astype(np.float16))
    feats = np.concatenate(out)
    path = work_dir(rec_id) / f"boss_feats_{short(name)}.npy"
    np.save(path, feats)
    print(f"{rec_id}: {feats.shape} -> {path}")


def main():
    name = sys.argv[sys.argv.index("--model") + 1] if "--model" in sys.argv else MODEL
    recs = recordings()
    for rec_id in (list(recs) if sys.argv[1] == "all" else [sys.argv[1]]):
        features(rec_id, name)


if __name__ == "__main__":
    main()
