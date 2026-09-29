# Quality results: blinded pairwise review (4-step probe)

Protocol: `blind-protocol.md`. The rater was Claude, a single rater. The three directories were scored and frozen in order (C vs B → C vs A → A vs B), and all keys stayed sealed until every score file was frozen.

| directory | key sha256 | frozen scores sha256 |
|---|---|---|
| blind-CvsB | `1a337522…` | `1965d634…` |
| blind-CvsA | `1dd3d97c…` | `c36c50d6…` |
| blind-AvsB | `80b3b425…` | `4b2b8f64…` |

The unblinded keys are in `key-*-unblinded.json`. The score sheets and per-composite notes are in `blind-*/SCORES-FROZEN.txt`.

## Tallies (overall preference, lexicographic: adherence > composition > visual quality)
| comparison | C better | other better | ties |
|---|---:|---:|---:|
| **C vs B** (Base + LoRA vs Turbo 4) | **6** | **18** (B) | 0 |
| **C vs A** (Base + LoRA vs Turbo 8 / FAST) | **8** | **16** (A) | 0 |
| **A vs B** (Turbo 8 vs Turbo 4, the control) | — | A 2 · B 3 | **19** |

## Which dimension decided each preference (recomputed from the frozen sheets + unblinded keys)
Overall preference is lexicographic: a pair goes to visual quality only when adherence and composition are equal.

| comparison | decided by **prompt adherence** | decided by **visual quality** (adherence equal) | composition |
|---|---|---|---|
| C vs B | **C 6** (p02 ×2, p09 ×2, p05-s6174, p12-s6174) · **B 5** (p06 ×2, p11-s4242, p12-s4242, p08-s6174) | **C 0 · B 13** | never decisive |
| C vs A | **C 8** (p02 ×2, p09 ×2, p05-s6174, p12-s6174, p07-s4242, p10-s4242) · **A 5** (p06 ×2, p11-s4242, p12-s4242, p08-s6174) | **C 0 · A 11** | never decisive |
| A vs B | A 2 (p05-s6174, p09-s6174) · B 2 (p09-s4242, p11-s4242) | A 0 · B 1 | never decisive |

- **Text:** in p05-s6174, C was exact while B added a garbled line and A duplicated "IMAGE". In p07, all arms were exact (C also won p07-s4242 on its vintage-poster look vs A's flat logo).
- **Counts (p12):** C was correct at s6174 but drew 4 plates at s4242. A and B were correct at s4242.
- **Artifacts** (attributed via the unblinded keys):
  - **C:** grain / 16-px grid in nearly all images; one duplicated balloon (p09-s6174 in the C-vs-B review).
  - **A (Turbo 8):** duplicated balloon (p09-s4242), a ghost wine glass (p11-s4242), a ghost pen clip (p04-s4242), "IMAGE" printed twice (p05-s6174).
  - **B (Turbo 4):** duplicated balloon (p09-s6174), a garbled extra line (p05-s6174).
  - Object duplication occurs in all three arms. It is not specific to 4-step sampling.

## Key observations
1. **All of C's losses were decided on visual quality, not prompt adherence.** Every pair C lost (13 vs B, 11 vs A) had equal adherence and composition, and was decided by C's consistent grain / 16-px grid. It is objectively measured (grid16 median 5.4 vs 1.1 for A and B; see `results.md`).
2. **On prompt adherence C was on par or slightly better:** 6–5 vs Turbo 4 and 8–5 vs FAST, on the pairs where adherence differed. These counts are too small to claim an advantage (sign test on 11 and 13 decisions: not significant). The pattern held across layout/attribute prompts: p02 subject placement and evening light, the p09 jeepney. The base model with its CFG-distilled LoRA may follow attributes more literally, but this is *suggestive*, not established.
3. **Turbo 4 ≈ Turbo 8 on this suite at 1024²** (A 2 / B 3 / 19 ties, and only object-level differences). That is stronger than the earlier step-sweep's "preview quality" label, which judged 400-px contact sheets unblinded, at seed 42.

## Limitations (disclosed)
- **Style recognisability:** C's grain made its images recognisable as "the grainy arm" in both C directories. The rater never knew which *label* the grainy arm had, but the blinding is weaker than in the Turbo-only gates.
- **Single AI rater, fast review.** Object-level judgements (counts, vehicles, duplicates) are more reliable than fine-texture judgements.
- 24 pairs per comparison, 2 seeds, 1024² only.
