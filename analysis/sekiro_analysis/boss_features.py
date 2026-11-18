"""DINOv2 features of the boss crops of a recording (boss_track.py), one row per crop.

Research use: python -I research/failure_attribution/scripts/boss_features.py <recording id | all> [--model ...]

Each crop is resized to 224×224 and goes through the pretrained model (timm). On the GPU (device "cuda", how every
research result was made) the model runs in fp16; on the CPU, in fp32. A row is the class token followed by the mean
of the patch tokens, L2-normalised separately, so either half can be used alone. Writes
<work>/boss_feats_<short model name>.npy (float16, rows in boss_track.csv order). `weights` names a local copy of the
model's weights (the worker has no network); without it timm downloads them.
"""
from pathlib import Path

import numpy as np
import timm
import torch

from .boss_track import load_crops

MODEL = "vit_small_patch14_dinov2.lvd142m"
MEAN, STD = (0.485, 0.456, 0.406), (0.229, 0.224, 0.225)


def short(name):
    return name.split(".")[0].replace("vit_", "").replace("_patch14_dinov2", "14")


def create_model(name=MODEL, device="cuda", weights=None):
    """The pretrained model, in fp16 on the GPU and fp32 on the CPU."""
    extra = {"pretrained_cfg_overlay": {"file": str(weights)}} if weights else {}
    model = timm.create_model(name, pretrained=True, num_classes=0, img_size=224, **extra).eval().to(device)
    return model.half() if device == "cuda" else model


def features(work, name=MODEL, device="cuda", batch=128, weights=None, progress=None):
    work = Path(work)
    half = device == "cuda"
    model = create_model(name, device, weights)
    crops = load_crops(work)                           # BGR uint8
    mean = torch.tensor(MEAN, device=device).view(1, 3, 1, 1)
    std = torch.tensor(STD, device=device).view(1, 3, 1, 1)
    out = []
    with torch.no_grad():
        for i in range(0, len(crops), batch):
            x = torch.from_numpy(crops[i:i + batch][..., ::-1].copy()).to(device).permute(0, 3, 1, 2).float() / 255
            x = torch.nn.functional.interpolate(x, size=(224, 224), mode="bilinear", antialias=True, align_corners=False)
            x = (x - mean) / std
            tokens = model.forward_features(x.half() if half else x).float()
            cls, patch = tokens[:, 0], tokens[:, 1:].mean(1)
            out.append(torch.cat([torch.nn.functional.normalize(cls, dim=1),
                                  torch.nn.functional.normalize(patch, dim=1)], 1).cpu().numpy().astype(np.float16))
            if progress:
                progress(min(1.0, (i + batch) / len(crops)))
    feats = np.concatenate(out)
    path = work / f"boss_feats_{short(name)}.npy"
    np.save(path, feats)
    print(f"{work.name}: {feats.shape} -> {path}")
    return path
