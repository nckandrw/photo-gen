# Session-scratch evidence preserved at the Phase 9 handoff (2026-10-09)

Phases 8 and 9 ran in one session (`a0de6674…`). Several files cited by committed docs lived only in that session's
scratch directory (`/private/tmp/claude-501/…/scratchpad/`), which does not survive the session. They were copied
here byte-for-byte (`cmp` verified, 0 mismatches) on 2026-10-09. Paths *inside* the copied files still name the
scratch directory; read them as "the original location". `SHA256SUMS` covers every file here, including the local-only
ones.

| here | what | cited by |
|---|---|---|
| `lock-inputs/req.in`, `lock-inputs/constraints.txt` | the exact inputs of `uv pip compile` for `../requirements.lock.txt` (its header names the scratch paths) | `../requirements.lock.txt`, `../PROTOCOL.md` |
| `lock-inputs/zimage-freeze.txt` | `pip freeze` of `mflux/.venv` at the time; `constraints.txt` is this minus mflux/mlx/mlx-metal, plus importlib-metadata 9.0.1 and zipp 4.1.0 | (provenance of the constraints) |
| `checks/pre/`, `checks/post/` | Phase 8 opening (00:49) and closing (05:15) checks: tests, `verify`, `verify --edit`, asset hashes | Phase 8 asset records, `../../PHASE8-INDEX.md` |
| `smoke/mlx/`, `smoke/ref/`, `smoke/ref2/` | the synthetic 640×480 smoke runs before the tool commit: `conditions.txt`, `monitor.csv`, `console.log`, `wrap.txt`, `data/record.json` (versioned); `data/*.npy`, `*.png` local only | `../PROTOCOL.md` amendment 1 (11.2 GB peak unbanded → 6.9 GB banded; 23 s → 13 s; `dec`/`dec_x12` byte-identical): `ref` = unbanded, `ref2` = banded |
| `smoke/convgate/conv-gate.json` | the banded-vs-unbanded convolution gate on the smoke (bit-exact) | `../PROTOCOL.md` amendment 1 |
| `glyph-crops/*.png` (local only) | the session assistant's glyph-height measurement crops (plain + ruler) for R02/R12/R15 t1–t5 | `../glyph-heights.json`, `../glyph-strata.md` |
| `cmp2/r02-1024-grid.png` (local only) | the gridded R02-1024 view used when drawing the Phase 8 CMP2 region | `../PROTOCOL.md` amendment 2 |

**Elsewhere:**
- Texture-Fix deletion `df` read-outs: `research/qwen/assets/df-{before,after}-texturefix-delete.txt` (provenance §9).
- Q-A desk-survey config files: `research/editing/qa-configs/`.
- Rater and annotator scratch: already in the repo (`../review/rater-crops/`, `../review-cmp2/rater-crops/`,
  `research/editing/compositing/review/rater-crops/`, `research/editing/compositing/annotation/audit/annotator-scratch/`).
  PNG sha256s are in `research/review-crops/MANIFEST.sha256`.

**Not preserved** (re-acquirable, binary):
- `dl-diffusers/`: the diffusers 0.40.0 and 0.41.0 wheels (PyPI). The 0.41.0 wheel that `torch-ref` was built from is at
  `torch-ref/dl/`.
- `dl-texturefix/`: the Texture-Fix repository's text files at revision `702909b4…`, which can be re-fetched. Their
  sha256s:
  - `config.json` `9785d527…a589ac` (as recorded at acquisition);
  - `LICENSE` `8dc973f0…72b28d` (byte-identical to the Qwen-Image-2.1 licence);
  - `NOTICE` `9277022b…a2d7`;
  - `README.md` `2a9e2b18…89ac`;
  - `fp16_demo.py` `74414d6a…05b8`.
