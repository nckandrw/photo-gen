"""Phase 8 Q-VR analysis (PROTOCOL.md sections 5-8): gates, tensor and image comparisons, the pre-registered tiers and
the classification, applied mechanically. Reads the run records under research/qwen/qv-reference/runs/ and Phase 7's
run records (for B_i and the reproduction hashes); never writes outside research/qwen/qv-reference/.

Usage: mflux/.venv/bin/python3.12 research/qwen/qv-reference/analyze_qvr.py <out.json> [<review_dir>]
  <review_dir> (optional, after unblinding): research/qwen/qv-reference/review with SCORES-FROZEN.csv and
  key-unblinded.json; adds the per-element text tallies (R_b, Q_b, TF, ID) and applies section 7 rules 3-5."""
import csv
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "research/editing"))
import tiler_port  # noqa: E402
from edit_metrics import _gray, ssim_map  # noqa: E402

RUNS = HERE / "runs"
P7 = ROOT / "research/qwen/runs"
BOXES = json.loads((ROOT / "research/qwen/qv/text-boxes.json").read_text())
ITEMS = [(b, t) for b in (512, 1024) for t in ("R02", "R12", "R15")]
LEGIBLE = {"PRESERVED", "DEGRADED"}


def js(p: Path) -> dict:
    return json.loads(p.read_text()) if p.exists() else {}


def d(arm: str, b: int, t: str) -> Path:
    return RUNS / f"{arm}-{b}-{t}" / "data"


def tensor_cmp(a: np.ndarray, b: np.ndarray) -> dict:
    a64, b64 = a.astype(np.float64), b.astype(np.float64)
    diff = a64 - b64
    fin = np.isfinite(a64) & np.isfinite(b64)
    nb = np.linalg.norm(b64[fin])
    pear = float(np.corrcoef(a64[fin].ravel(), b64[fin].ravel())[0, 1]) if fin.sum() > 1 else None
    def st(x):
        f = np.isfinite(x)
        return {"min": float(x[f].min()), "max": float(x[f].max()), "mean": float(x[f].mean()), "var": float(x[f].var()),
                "nonfinite": int((~f).sum())}
    return {"shape": list(a.shape), "dtype": str(a.dtype), "a": st(a64), "b": st(b64), "mae": float(np.abs(diff[fin]).mean()),
            "max_abs": float(np.abs(diff[fin]).max()), "rms": float(np.sqrt((diff[fin] ** 2).mean())),
            "rel_l2": float(np.linalg.norm(diff[fin]) / nb) if nb > 0 else None, "pearson": pear,
            "elements_differing": int((a != b).sum()), "fraction_differing": float((a != b).mean())}


def psnr(a: np.ndarray, b: np.ndarray) -> float | None:
    mse = float(((a.astype(np.float64) - b.astype(np.float64)) ** 2).mean())
    return round(10 * math.log10(255 ** 2 / mse), 3) if mse > 0 else None


def boxes(t: str, h: int, w: int):
    for el, (x0, y0, x1, y1) in BOXES[t].items():
        yield el, slice(int(y0 * h), max(int(y0 * h) + 1, math.ceil(y1 * h))), slice(int(x0 * w), max(int(x0 * w) + 1, math.ceil(x1 * w)))


def image_cmp(x: np.ndarray, ref: np.ndarray, d0: np.ndarray, t: str, b_i: float) -> dict:
    """x, ref: (H, W, 4) uint8 (to_uint8 of the float decoder outputs); d0: (H, W, 3) uint8. ref is A2."""
    xr, rr = x[..., :3], ref[..., :3]
    mae_rgba = float(np.abs(x.astype(np.int16) - ref.astype(np.int16)).mean())
    mae_rgb = float(np.abs(xr.astype(np.int16) - rr.astype(np.int16)).mean())
    p_x, p_r = psnr(xr, d0), psnr(rr, d0)
    dpsnr = round(p_r - p_x, 4)
    tier = "PE" if mae_rgba <= b_i else ("MATERIAL" if (mae_rgb >= 1.0 or abs(dpsnr) >= 0.5) else "SMALL")
    gx, gr, g0 = _gray(xr.astype(np.float64)), _gray(rr.astype(np.float64)), _gray(d0.astype(np.float64))
    sx, sr = ssim_map(gx, g0), ssim_map(gr, g0)
    h, w = d0.shape[:2]
    reg = {el: {"mae_vs_ref": round(float(np.abs(xr[ys, xs].astype(np.int16) - rr[ys, xs].astype(np.int16)).mean()), 4),
                "max_vs_ref": int(np.abs(xr[ys, xs].astype(np.int16) - rr[ys, xs].astype(np.int16)).max()),
                "psnr_x_d0": psnr(xr[ys, xs], d0[ys, xs]), "psnr_ref_d0": psnr(rr[ys, xs], d0[ys, xs]),
                "ssim_x_d0": round(float(sx[ys, xs].mean()), 4), "ssim_ref_d0": round(float(sr[ys, xs].mean()), 4)}
           for el, ys, xs in boxes(t, h, w)}
    return {"mae_rgba": round(mae_rgba, 5), "mae_rgb": round(mae_rgb, 5),
            "max_abs": int(np.abs(x.astype(np.int16) - ref.astype(np.int16)).max()),
            "pixels_differing": round(float((x != ref).any(-1).mean()), 6), "psnr_x_ref": psnr(xr, rr),
            "psnr_x_d0": p_x, "psnr_ref_d0": p_r, "dpsnr_ref_minus_x": dpsnr,
            "ssim_x_d0": round(float(sx.mean()), 5), "ssim_ref_d0": round(float(sr.mean()), 5),
            "B_i": b_i, "tier": tier, "text_boxes": reg}


def u8(p: Path) -> np.ndarray:
    return tiler_port.to_uint8(np.load(p))


def gates() -> dict:
    g = {"weights": js(RUNS / "GATE-weights/data/weight-identity.json").get("pass"),
         "conv_banding": js(RUNS / "GATE-conv/data/conv-gate.json").get("all_bit_exact"),
         "per_item": {}}
    for b, t in ITEMS:
        a1, a2 = js(d("A1", b, t) / "record.json"), js(d("A2", b, t) / "record.json")
        p7 = js(P7 / f"QV-{b}-{t}-a/worker/identity.json")
        if not a1 or not a2:
            g["per_item"][f"{t}-{b}"] = {"missing": True}
            continue
        g["per_item"][f"{t}-{b}"] = {
            "a1_params": a1["param_check"]["pass"],
            "a1_reproduces_phase7_roundtrip": a1["identity"]["roundtrip"]["pixel_sha256"] == p7["roundtrip"]["pixel_sha256"],
            "a1_reproduces_phase7_input": a1["identity"]["input"]["pixel_sha256"] == p7["input"]["pixel_sha256"],
            "a1_cast_commutes": a1["cast_commutes_with_pack"], "a1_to_uint8_port": a1["to_uint8_port_vs_to_pil"]["pass"],
            "a1_tiler_gate": a1.get("tiler_gate", {}).get("pass"),
            "a2_preprocessing": a2["preprocessing_gate"]["pass"], "a2_cast": a2["cast_gate"]["pass"],
            "a2_finite": all(a2["finite"].values()), "a2_vae_loaded_equals_file": a2["vae"]["loaded_equals_file"]}
    a2a, a2b = js(d("A2", 512, "R12") / "record.json"), js(RUNS / "A2b-512-R12/data/record.json")
    g["a2_determinism"] = bool(a2a and a2b and all(a2a["arrays"][k]["sha256"] == a2b["arrays"][k]["sha256"] for k in a2a["arrays"]))
    tiler = [v["a1_tiler_gate"] for v in g["per_item"].values() if v.get("a1_tiler_gate") is not None]
    g["tiler_gate_items"] = len(tiler)
    item_ok = all(all(x is not False for k, x in v.items() if k != "a1_tiler_gate") and not v.get("missing")
                  for v in g["per_item"].values())
    g["all_pass"] = bool(g["weights"] and g["conv_banding"] and item_ok and g["a2_determinism"]
                         and len(tiler) >= 2 and all(tiler))
    return g


def review_tallies(review: Path) -> dict:
    key = json.loads((review / "key-unblinded.json").read_text())
    rows = {r["id"]: r for r in csv.DictReader((review / "SCORES-FROZEN.csv").open())}
    calls: dict = {}
    for sheet, k in key.items():
        if k.get("kind") != "item":
            continue
        for label, arm in k["panels"].items():
            r = rows[f"{sheet}-{label}"]
            for n in range(1, 6):
                v = r.get(f"t{n}", "-")
                if v not in ("-", ""):
                    calls.setdefault((k["budget"], k["task"], f"t{n}"), {})[arm] = v
    def cnt(b, x, y):  # legible in x, not in y
        return sum(1 for (bb, _, _), c in calls.items() if bb == b and x in c and y in c
                   and c[x] in LEGIBLE and c[y] not in LEGIBLE)
    out = {"calls": {f"{t}-{b}-{e}": c for (b, t, e), c in sorted(calls.items())}}
    for b in (512, 1024):
        out[b] = {"R_A2_not_A1": cnt(b, "A2", "A1"), "Q_A1_not_A2": cnt(b, "A1", "A2"),
                  "R_TF_not_A2": cnt(b, "TF", "A2"), "Q_A2_not_TF": cnt(b, "A2", "TF"),
                  "ID_lost_vs_A1": cnt(b, "A1", "ID"), "ID_gained_vs_A1": cnt(b, "ID", "A1"),
                  "legible": {arm: sum(1 for (bb, _, _), c in calls.items() if bb == b and c.get(arm) in LEGIBLE)
                              for arm in ("D0", "A1", "A2", "TF", "ID")}}
    return out


def classify(g: dict, tiers: dict, tally: dict | None) -> str:
    if not g["all_pass"]:
        return "INCONCLUSIVE"
    vals = list(tiers.values())
    if all(v["tier"] == "PE" for v in vals):
        return "RUNTIME-MATCHED"
    mat_pos = sum(v["tier"] == "MATERIAL" and v["dpsnr_ref_minus_x"] >= 0.5 for v in vals)
    mat_neg = sum(v["tier"] == "MATERIAL" and v["dpsnr_ref_minus_x"] <= -0.5 for v in vals)
    if tally is None:
        return "PENDING-REVIEW" if not any(v["tier"] == "MATERIAL" for v in vals) else (
            "MLX-DEGRADED" if mat_pos >= 2 and mat_neg < 2 else ("REFERENCE-DEGRADED" if mat_neg >= 2 and mat_pos < 2
                                                                 else "PENDING-REVIEW"))
    rq = [tally[b]["R_A2_not_A1"] - tally[b]["Q_A1_not_A2"] for b in (512, 1024)]
    mlx = mat_pos >= 2 or any(x >= 2 for x in rq)
    ref = mat_neg >= 2 or any(x <= -2 for x in rq)
    if mlx and ref:
        return "INCONCLUSIVE"
    if mlx:
        return "MLX-DEGRADED"
    if ref:
        return "REFERENCE-DEGRADED"
    if not any(v["tier"] == "MATERIAL" for v in vals) and all(abs(x) <= 1 for x in rq):
        return "RUNTIME-MATCHED"
    return "INCONCLUSIVE"


def main(out_json: str, review: str | None = None) -> None:
    g = gates()
    items, tiers, t32 = {}, {}, {}
    for b, t in ITEMS:
        a1d, a2d, a1t = d("A1", b, t), d("A2", b, t), d("A1T", b, t)
        if not (a1d / "dec.npy").exists() or not (a2d / "dec.npy").exists():
            continue
        b_i = js(P7 / f"QV-{b}-{t}-a/worker/identity.json")["variants"]["fp32-latents"]["mean_abs_diff"]
        d0 = np.asarray(Image.open(P7 / f"QV-{b}-{t}-a/worker/input.png").convert("RGB"))
        A1, A2, X12 = u8(a1d / "dec.npy"), u8(a2d / "dec.npy"), u8(a2d / "dec_x12.npy")
        rec = {"tensors": {k: tensor_cmp(np.load(a1d / f"{k}.npy"), np.load(a2d / f"{k}.npy"))
                           for k in ("moments", "z_norm", "z_dec_in", "dec")},  # x_in: A2 reads A1's (gate 4 re-derives it)
               "decoder_only_x12_vs_a1": tensor_cmp(np.load(a2d / "dec_x12.npy"), np.load(a1d / "dec.npy")),
               "image_a1_vs_a2": image_cmp(A1, A2, d0, t, b_i),
               "image_x12_vs_a1": {"mae_rgba": round(float(np.abs(X12.astype(np.int16) - A1.astype(np.int16)).mean()), 5),
                                   "max_abs": int(np.abs(X12.astype(np.int16) - A1.astype(np.int16)).max()),
                                   "psnr": psnr(X12[..., :3], A1[..., :3])},
               "alpha": {arm: {"min": int(x[..., 3].min()), "mean": round(float(x[..., 3].mean()), 3)}
                         for arm, x in (("A1", A1), ("A2", A2))}}
        if (a1t / "dec.npy").exists():
            A1T = u8(a1t / "dec.npy")
            rec["a1t"] = {"image_a1t_vs_a2": image_cmp(A1T, A2, d0, t, b_i),
                          "image_a1t_vs_a1_mae_rgba": round(float(np.abs(A1T.astype(np.int16) - A1.astype(np.int16)).mean()), 5),
                          "z_norm_a1t_vs_a2": tensor_cmp(np.load(a1t / "z_norm.npy"), np.load(a2d / "z_norm.npy")),
                          "z_norm_a1t_vs_a1": tensor_cmp(np.load(a1t / "z_norm.npy"), np.load(a1d / "z_norm.npy"))}
            t32[f"{t}-{b}"] = rec["a1t"]["image_a1t_vs_a2"]["tier"]
        zr = rec["tensors"]["z_norm"]["rel_l2"]
        rec["z_norm_wording"] = ("agreement at fp32/TF32 rounding level" if zr <= 1e-3 else
                                 "material latent mismatch" if zr >= 1e-2 else "between the pre-registered wordings")
        items[f"{t}-{b}"] = rec
        tiers[f"{t}-{b}"] = {k: rec["image_a1_vs_a2"][k] for k in ("tier", "mae_rgba", "mae_rgb", "dpsnr_ref_minus_x", "B_i")}
    tally = review_tallies(Path(review)) if review else None
    cls = classify(g, tiers, tally)
    attribution = None
    if tiers and any(v["tier"] != "PE" for v in tiers.values()) and t32:
        attribution = ("precision-mode difference (documented MLX default), not a defect"
                       if all(t32.get(k) == "PE" for k, v in tiers.items() if v["tier"] != "PE") else
                       "not attributable to TF32 alone")
    summary = {"tool": "research/qwen/qv-reference/analyze_qvr.py", "classification": cls, "gates": g, "tiers": tiers,
               "tf32_off_tiers": t32, "tf32_attribution": attribution, "review": tally, "items": items,
               "probes": {"mlx": {k: js(RUNS / "PROBE-mlx/data/probe.json").get(k) for k in ("pass", "distinct_pad_calls", "temporal_avgdown_sites")},
                          "mps_positive_control": {k: js(RUNS / "PROBE-mps/data/mps-probe.json").get(k) for k in ("defect_reproduced", "torch")}},
               "inputs_sha256": {str(p.relative_to(HERE)): hashlib.sha256(p.read_bytes()).hexdigest() for p in
                                 sorted(RUNS.glob("*/data/*.json"))}}
    Path(out_json).write_text(json.dumps(summary, indent=1) + "\n")
    print("classification", cls, "| gates", g["all_pass"], "| tiers", {k: v["tier"] for k, v in tiers.items()},
          "| A1T tiers", t32, "| attribution", attribution)


if __name__ == "__main__":
    main(*sys.argv[1:])
