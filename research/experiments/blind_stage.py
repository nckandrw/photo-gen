#!/usr/bin/env python3
"""Controlled blind-review stages (protocol adopted 2026-09-25 after the teab key incident; see BLIND-PROTOCOL.md).

  prepare  <pairs.json> <blind_dir> <seed>   hash every input image; create blind_dir (must NOT exist);
                                             write the L/R key ATOMICALLY (tmp + rename) BEFORE any composite;
                                             render composites; write MANIFEST.json (input, key and composite
                                             hashes). On any failure: write INCIDENT-<ts>.json and stop
                                             (nothing is deleted).
  freeze   <blind_dir> <scores_file>         copy scores into blind_dir/SCORES-FROZEN.<ext>, record sha256
                                             in MANIFEST.json, make read-only. Refuses if already frozen.
  unblind  <blind_dir>                       refuses unless scores are frozen and unchanged, and the key is
                                             unchanged since prepare; then prints the key.
pairs.json: [[name, pathA, pathB], ...]  (paths relative to CWD). The key file is never read before `unblind`.
"""
import hashlib, json, os, random, shutil, sys, time, traceback
from PIL import Image, ImageDraw

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""): h.update(c)
    return h.hexdigest()

def atomic_json(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w") as f: json.dump(obj, f, indent=1); f.flush(); os.fsync(f.fileno())
    os.replace(tmp, path)

def incident(d, stage, err):
    os.makedirs(d, exist_ok=True)
    p = f"{d}/INCIDENT-{time.strftime('%Y%m%dT%H%M%S')}.json"
    atomic_json(p, {"stage": stage, "error": str(err), "traceback": traceback.format_exc(),
                    "note": "blind artifacts left in place; decide whether blinding could be compromised"})
    print(f"INCIDENT recorded: {p}", file=sys.stderr)

def composite(a, b, label):
    A, B = Image.open(a).convert("RGB"), Image.open(b).convert("RGB")
    W, H, pad, top = A.width + B.width + 16, max(A.height, B.height), 16, 40
    c = Image.new("RGB", (W, H + top), "white"); d = ImageDraw.Draw(c)
    c.paste(A, (0, top)); c.paste(B, (A.width + pad, top))
    d.text((8, 12), f"{label}  LEFT", fill="black"); d.text((A.width + pad + 8, 12), "RIGHT", fill="black")
    return c

def prepare(pairs_path, bd, seed):
    if os.path.exists(bd):
        sys.exit(f"refusing: {bd} exists (never reuse or overwrite a blind directory)")
    pairs = json.load(open(pairs_path))
    try:
        inputs = {p: sha(p) for _, a, b in pairs for p in (a, b)}  # fails early if any input is missing
        os.makedirs(bd)
        rng = random.Random(int(seed))
        key = {}
        for i, (name, a, b) in enumerate(pairs):
            swap = rng.random() < 0.5
            key[f"C{i + 1:02d}"] = {"pair": name, "left": b if swap else a, "right": a if swap else b}
        key_path = f"{bd}/.KEY-DO-NOT-OPEN-BEFORE-FREEZE.json"
        atomic_json(key_path, key)
        comps = {}
        for c, k in key.items():
            p = f"{bd}/{c}.png"; composite(k["left"], k["right"], c).save(p + ".tmp.png"); os.replace(p + ".tmp.png", p)
            comps[c] = sha(p)
        atomic_json(f"{bd}/MANIFEST.json", {"created": time.strftime("%Y-%m-%dT%H:%M:%S"), "seed": int(seed),
                    "pairs_file": pairs_path, "pairs_sha256": sha(pairs_path), "inputs": inputs,
                    "key_sha256": sha(key_path), "composites": comps, "scores_frozen": None})
        os.chmod(key_path, 0o444)
        print(f"prepared {len(key)} composites in {bd}; key sha256 {sha(key_path)}")
    except Exception as e:
        incident(bd if os.path.isdir(bd) else os.path.dirname(os.path.abspath(bd)), "prepare", e); raise

def freeze(bd, scores):
    m = json.load(open(f"{bd}/MANIFEST.json"))
    if m.get("scores_frozen"): sys.exit("refusing: scores already frozen")
    dst = f"{bd}/SCORES-FROZEN{os.path.splitext(scores)[1]}"
    shutil.copyfile(scores, dst); os.chmod(dst, 0o444)
    m["scores_frozen"] = {"file": dst, "sha256": sha(dst), "at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    os.chmod(f"{bd}/MANIFEST.json", 0o644); atomic_json(f"{bd}/MANIFEST.json", m); os.chmod(f"{bd}/MANIFEST.json", 0o444)
    print(f"frozen {dst} sha256 {m['scores_frozen']['sha256']}")

def unblind(bd):
    m = json.load(open(f"{bd}/MANIFEST.json"))
    fz = m.get("scores_frozen")
    if not fz: sys.exit("refusing: scores not frozen")
    if sha(fz["file"]) != fz["sha256"]: sys.exit("refusing: frozen scores changed")
    kp = f"{bd}/.KEY-DO-NOT-OPEN-BEFORE-FREEZE.json"
    if sha(kp) != m["key_sha256"]: sys.exit("refusing: key changed since prepare")
    print(open(kp).read())

if __name__ == "__main__":
    cmd = sys.argv[1]
    {"prepare": lambda: prepare(*sys.argv[2:5]), "freeze": lambda: freeze(*sys.argv[2:4]),
     "unblind": lambda: unblind(sys.argv[2])}[cmd]()
