#!/usr/bin/env python3
"""Merge per-prompt FFN calibration npz files (p3b/calib-*.npz) into p3b/ffn-scores.npz (mean over prompts)."""
import glob, numpy as np
fs = sorted(glob.glob("p3b/calib-c*.npz")); assert fs, "no calibration files"
d = [np.load(f) for f in fs]; keys = d[0].files
np.savez("p3b/ffn-scores.npz", **{k: np.mean([x[k] for x in d], axis=0) for k in keys})
print(f"merged {len(fs)} prompts, {len(keys)} blocks -> p3b/ffn-scores.npz")
