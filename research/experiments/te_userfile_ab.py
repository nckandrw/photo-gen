"""CLOSED 2026-09-25: the heretic-v2 branch was rejected; by decision this harness is NOT to be run (kept as history).
Stock vs substitute text-encoder A/B on a USER-SUPPLIED prompt file (run locally by the user).

Content boundary (agreed 2026-09-24):
  * Prompts are read from the user's file only; this script contains none.
  * Any prompt that references minors (age terms, school/child vocabulary, ages under 18) is REFUSED:
    it is never encoded or generated, and only the refusal count is reported. This is a hard block, not a filter
    that can be switched off by a flag. It is English-only: any prompt containing non-ASCII characters (other
    than typographic quotes/dashes) is refused, because the vocabulary check cannot read other languages.
    Regression cases: te_userfile_ab_selftest.py (run it after any change to the block).
  * Images are written to the user's output folder for the USER to review. The report contains only
    content-agnostic aggregates (conditioning drift, pixel-difference statistics, timing) — no prompt text.

Usage (from research/experiments):
  ~/Dev/photo-gen/mflux/.venv/bin/python3.12 te_userfile_ab.py <prompts.txt> <out_dir> [--te-model <composite dir>] [--res 1024] [--seed 42]
     [--precision bf16] [--drift-only]
prompts.txt: one prompt per line; blank lines and lines starting with '#' are ignored.
Writes <out_dir>/report.json (aggregates) and <out_dir>/images/<nnn>-{stock,cand}.png.
"""
from __future__ import annotations

import argparse, json, os, re, statistics, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PY = ROOT / "mflux/.venv/bin/python3.12"
STOCK = ROOT / "models/mflux/z-image-turbo-mflux-q4"
DEFAULT_CAND = ROOT / "models/mflux/composites/zimage-turbo-q4-te-heretic-v2"

_MINOR_TERMS = r"""child|children|childlike|childhood|kid|kids|kiddo|kiddie|minor|minors|underage[d]?|under-age[d]?|under\s*18|
preteen[s]?|pre-teen[s]?|teen[s]?|teenage[d]?|teenager[s]?|teeny|tween[s]?|adolescen\w*|juvenile[s]?|youth[s]?|youngster[s]?|
toddler[s]?|infant[s]?|baby|babies|newborn[s]?|loli\w*|shota\w*|jailbait|pupil[s]?|schoolchild(ren)?|school\s*child(ren)?|
schoolgirl[s]?|schoolboy[s]?|school\s*girl[s]?|school\s*boy[s]?|school\s*uniform[s]?|middle\s*school\w*|grade\s*school\w*|
primary\s*school\w*|elementary|kindergarten\w*|junior\s*high|high\s*school\w*|pubescent|prepubescent|puberty|
little\s+(girl|boy)[s]?|young\s+(girl|boy)[s]?|boy[s]?|girl[s]?|girlie|daughter[s]?|son[s]?|niece[s]?|nephew[s]?|
student\s+(girl|boy)[s]?|cub[s]?|chibi|petite\s+young|underdeveloped|flat[-\s]?chested"""
_MINOR_RE = re.compile(r"\b(" + re.sub(r"\s*\n\s*", "", _MINOR_TERMS) + r")\b", re.IGNORECASE)
_NUM_WORDS = (r"one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen")
_AGE_NUM = rf"([0-9]|1[0-7]|{_NUM_WORDS})"
_AGE_RE = re.compile(
    rf"\b{_AGE_NUM}\s*(-|\s)?\s*(y/?o|yo|yrs?|years?|yr\.?)(\s*-?\s*old)?\b"   # 15 yo, fifteen-year-old
    rf"|\bage[sd]?\s*(of\s*)?{_AGE_NUM}\b"                                      # aged 12, age of twelve
    rf"|\b{_AGE_NUM}\s*(th|st|nd|rd)?\s*grade(r|rs)?\b"                          # 7th grade, fifth grader
    rf"|\b(first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|eleventh|twelfth)\s*-?\s*grade(r|rs)?\b"  # fifth grade
    rf"|\b(thir|four|fif|six|seven)teen(s)?\b(?!\s*-?\s*(hundred|thousand))",  # bare 13-17 words (not 'seventeen-hundreds')
    re.IGNORECASE)


def refused(prompt: str) -> bool:
    """Hard block. Over-inclusive by design (e.g. 'girl'/'boy' are refused even when adult is meant:
    rephrase as 'woman'/'man'/'adult'). LIMITATION: English vocabulary only — the text encoder understands other
    languages, so prompts must be written in English; non-ASCII-letter prompts are refused outright."""
    if re.search(r"[^\x00-\x7F\u2018\u2019\u201c\u201d\u2013\u2014]", prompt):  # non-English/non-ASCII: refuse
        return True
    return bool(_MINOR_RE.search(prompt) or _AGE_RE.search(prompt))


def run(cmd: list[str]) -> str:
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"command failed ({p.returncode}): {p.stderr[-2000:]}")
    return p.stdout


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("prompts"); ap.add_argument("out_dir")
    ap.add_argument("--te-model", default=str(DEFAULT_CAND))
    ap.add_argument("--res", type=int, default=1024); ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--precision", choices=["fp32", "bf16"], default="bf16")
    ap.add_argument("--drift-only", action="store_true", help="conditioning drift only; no images")
    a = ap.parse_args()

    lines = [l.strip() for l in Path(a.prompts).read_text().splitlines()]
    prompts = [l for l in lines if l and not l.startswith("#")]
    kept = [p for p in prompts if not refused(p)]
    n_refused = len(prompts) - len(kept)
    out = Path(a.out_dir); (out / "images").mkdir(parents=True, exist_ok=True)
    report = {"prompts_in_file": len(prompts), "refused_minor_block": n_refused, "evaluated": len(kept),
              "te_model": a.te_model, "res": a.res, "seed": a.seed, "precision": a.precision}
    if not kept:
        print(json.dumps(report, indent=1)); (out / "report.json").write_text(json.dumps(report, indent=1)); return 0

    # 1) conditioning drift (content-agnostic numbers only)
    with tempfile.TemporaryDirectory() as td:
        pj, dj = Path(td) / "p.json", Path(td) / "d.json"
        pj.write_text(json.dumps({"user": {f"u{i:03d}": p for i, p in enumerate(kept)}}))
        run([str(PY), str(HERE / "te_drift.py"), str(STOCK), str(Path(a.te_model) / "text_encoder"), str(pj), str(dj)])
        report["drift"] = json.loads(dj.read_text())["by_set"]["user"]

    # 2) images (for the user's own review) + pixel-difference aggregates
    if not a.drift_only:
        import numpy as np
        from PIL import Image
        diffs, times = [], {"stock": [], "cand": []}
        for i, p in enumerate(kept):
            imgs = {}
            for arm, model in (("stock", None), ("cand", a.te_model)):
                o = out / "images" / f"{i:03d}-{arm}.png"
                cmd = [str(PY), str(HERE / "exp_zimage.py"), f"--prompt={p}", "--seed", str(a.seed),
                       "--precision", a.precision, "--width", str(a.res), "--height", str(a.res), "--out", str(o)]
                if model:
                    cmd += ["--model", model]
                res = json.loads(run(cmd).split("EXPRESULT ", 1)[1])
                times[arm].append(res["denoise_s"])
                imgs[arm] = np.asarray(Image.open(o).convert("RGB"), dtype=np.float64)
            mse = float(((imgs["stock"] - imgs["cand"]) ** 2).mean())
            diffs.append({"psnr": 99.0 if mse == 0 else round(float(10 * np.log10(255 ** 2 / mse)), 2),
                          "mean_abs": round(float(np.abs(imgs["stock"] - imgs["cand"]).mean()), 2)})
            print(f"{i + 1}/{len(kept)} done", file=sys.stderr, flush=True)
        ps = [d["psnr"] for d in diffs]
        report["pixel_diff"] = {"psnr_median": statistics.median(ps), "psnr_min": min(ps), "psnr_max": max(ps),
                                "identical": int(sum(p == 99.0 for p in ps)),
                                "mean_abs_median": statistics.median(d["mean_abs"] for d in diffs)}
        report["denoise_s_median"] = {k: statistics.median(v) for k, v in times.items()}
        report["review_note"] = ("Per-image judgement (does the substitute follow the prompt where stock does not?) "
                                 "is left to the user: images/<nnn>-stock.png vs images/<nnn>-cand.png.")
    (out / "report.json").write_text(json.dumps(report, indent=1, default=float))
    print(json.dumps(report, indent=1, default=float))
    return 0


if __name__ == "__main__":
    sys.exit(main())
