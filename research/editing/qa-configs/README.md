# Q-A desk-survey config files (Phase 8, fetched 2026-10-09)

These are the Hugging Face config files that `../QA-ALTERNATIVE-MODELS.md` cites under "Sources". For each candidate
there are three: `model_index.json`, `transformer/config.json` and `vae/config.json`, saved as `<org>_<repo>__<file>`.
They were fetched from the repository heads on 2026-10-09. The four shortlisted revisions are in
`QA-ALTERNATIVE-MODELS.md` §2:
- FLUX.2-klein-4B `e7b7dc27f9`;
- Qwen-Image-Edit-2511 `6f3ccc0b56`;
- LongCat-Image-Edit `7b54ef423a`;
- Qwen-Image-Layered `8f0ca708df`.

OmniGen2 and Step1X-Edit v1.2 were read at their heads on the same day.

The files are metadata only, with no weights. They were copied from session scratch at the Phase 9 handoff;
`SHA256SUMS` lists them. A later screen (e.g. the FLUX.2 VAE round trip) must re-fetch at the pinned revision and
compare against these files, not trust them as current.
