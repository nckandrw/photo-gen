# PHOTO-GEN editing benchmark: real-world photographs (v1)

**This benchmark belongs to PHOTO-GEN, not to any model.** The source photographs, the task definitions and the rubric here are model-independent. Results for a particular backend go to that backend's report, e.g. `research/qwen/QWEN-EDITING-QUALITY.md` § G2.

```text
PHOTO-GEN BENCHMARK
├── generation/          → research/experiments/            (Z-Image: FAST/BALANCED/ULTRA gates)
└── editing/             → research/editing/
    ├── synthetic-controls → research/editing/ (suite v1, E01–E11; Z-Image-generated sources; gate G0)
    └── real-world         → research/editing/real-world/ (this directory; real camera photographs; gate G2)
                              results per backend: research/qwen/ (Qwen-Image-2.1 on mflux 0.21.0)
```

The synthetic-control suite stays where it is (`research/editing/suite-v1.json`, `sources.json`, `regions.json`), because committed G0 reports and tools reference those paths. The tree above is the logical layout (directive §26). This is an Improvement Clause choice: no file moves, no broken evidence paths.

## Why real photographs
G0 used Z-Image-generated sources. Those are clean, centred, noise-free renders of prompts, and they don't represent what a user actually edits. Real camera photographs bring sensor noise, JPEG compression, clutter, odd lighting, real text, transparent and reflective objects, and arbitrary aspect ratios. G2 is therefore the main quality evidence for real use. G0 remains a controlled capability check.

## Files
| file | content |
|---|---|
| `selection.json` | the 16 chosen Commons files and why they qualified (CC0/PD, camera photograph, input limits, no public figures or minors) |
| `fetch_sources.py` | acquisition: Commons API metadata, own-directory download, SHA-1 check, SHA-256, EXIF/ICC, staging through photo-gen's input code |
| `source-manifest.json` | per source: Commons URL, licence, creator/credit, original filename, file SHA-1/SHA-256, pixel SHA-256 (staged), dimensions, format, EXIF camera and orientation, ICC profile |
| `task-manifest.json` | one pre-registered task per source: instruction, MUST CHANGE, MUST NOT CHANGE, text criterion, seeds, regions |
| `protocol.md` | the G2 pre-registration: runs, provenance-blind scoring, rubric, numeric pass criteria, memory/UX classes, decision rule |
| `g2_blind.py` | provenance-blind review tool (prepare → freeze → unblind) |
| `benchmark.csv` | one row per run: identity, timing, memory, pressure |
| `scores.csv` | frozen rater scores joined with the unblinded mapping |
| `results.md` | the G2 outcome |

## Licensing and storage
- **Licences.** Only **CC0** or **public domain** photographs from Wikimedia Commons are used. The licence is re-read from the Commons API at download time, and anything else is rejected. Creator and credit are recorded even where attribution isn't required.
- **Not committed.** Images are never committed (repository image policy): originals live in `data/benchmark/real-world/originals/<id>/` (gitignored), staged copies in `data/inputs/<pixel_sha256>.png`, and outputs and composites are gitignored. Each image's identity is committed as hashes, and its URL lets it be re-acquired.
- **People.** Adults only, no public figures, and no edit that alters a person's identity (R01 changes clothing colour; R12 removes one passer-by from a crowd). Outputs aren't published.
