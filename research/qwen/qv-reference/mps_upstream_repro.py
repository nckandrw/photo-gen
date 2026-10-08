"""Phase 8 Q-VR, post-hoc diagnostic (descriptive; added after PROBE-mps came back negative, never part of the
classification): do the upstream reports' OWN minimal reproductions of the PyTorch-MPS temporal-pad defect reproduce on
this machine (torch 2.14.0 in torch-ref/.venv, macOS 27, M5)? Synthetic data only.

Cases, verbatim from the reports:
  pytorch #194922: torch.manual_seed(3); x = randn(1, 3, 9, 256, 544); F.pad(x, (0,0,0,0,2,0)) on MPS vs CPU (fp32)
  ComfyUI #16433 comment (buggz2k): torch.manual_seed(41); randn(1, 8, 1, H, W), H x W in 128x192 / 256x384 / 512x512,
                                    F.pad(x, (0,0,0,0,1,0)), fp32 and bf16
  mflux qwen21 VALIDATION.md: ones((1, 96, 1, 256, 256)) padded with (0,0,0,0,1,0) (reported to return zeros)

Run: torch-ref/.venv/bin/python3.12 -I research/qwen/qv-reference/mps_upstream_repro.py <out.json>"""
import json
import platform
import sys
from pathlib import Path

import torch
import torch.nn.functional as F


def cmp(x: torch.Tensor, pad) -> dict:
    want = F.pad(x, pad).float()
    got = F.pad(x.to("mps"), pad).float().cpu()
    return {"shape": list(x.shape), "pad": list(pad), "dtype": str(x.dtype), "bit_exact": bool(torch.equal(got, want)),
            "fraction_differing": float((got != want).float().mean()), "nonfinite": int((~torch.isfinite(got)).sum()),
            "max_abs": float(torch.nan_to_num((got - want).abs(), nan=float("inf")).max())}


def main(out: str) -> None:
    rows = []
    torch.manual_seed(3)
    rows.append({"case": "pytorch#194922", **cmp(torch.randn(1, 3, 9, 256, 544), (0, 0, 0, 0, 2, 0))})
    torch.manual_seed(41)
    for dt in (torch.float32, torch.bfloat16):
        for h, w in ((128, 192), (256, 384), (512, 512)):
            rows.append({"case": "ComfyUI#16433", **cmp(torch.randn(1, 8, 1, h, w).to(dt), (0, 0, 0, 0, 1, 0))})
    rows.append({"case": "mflux VALIDATION ones", **cmp(torch.ones(1, 96, 1, 256, 256), (0, 0, 0, 0, 1, 0))})
    rec = {"tool": "research/qwen/qv-reference/mps_upstream_repro.py", "role": "post-hoc diagnostic (descriptive)",
           "torch": torch.__version__, "mac_ver": platform.mac_ver()[0], "machine": platform.machine(),
           "mps_available": torch.backends.mps.is_available(), "rows": rows,
           "any_reproduced": any(not r["bit_exact"] for r in rows)}
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps({"any_reproduced": rec["any_reproduced"], "mac_ver": rec["mac_ver"],
                      "rows": [(r["case"], r["shape"], r["dtype"], r["bit_exact"]) for r in rows]}, indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
