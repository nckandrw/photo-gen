"""E02: Z-Image DiT with a bf16 hidden stream (production mflux 0.20.0 promotes it to float32; see e01).
Runtime patch inside this experiment process only (no files modified):
  - transformer.x_pad_token / cap_pad_token cast to the model precision (bf16)
  - TimestepEmbedder output cast to bf16 (so adaLN modulation stays bf16)
Then runs the unmodified Turbo CLI main() with production arguments (--low-ram, 9 steps) and records timings + dtypes.
Usage: e02_bf16_hidden_stream.py <out.png> <prompt> [W H seed]"""
import json, sys, time
import mlx.core as mx
from mflux.models.z_image.model.z_image_transformer import timestep_embedder as TE, attention as A
import mflux.models.z_image.variants.z_image as zmod
from mflux.models.z_image.cli import z_image_turbo_generate as cli

pos = [a for a in sys.argv[1:] if not a.startswith("--")]
out, prompt = pos[0], pos[1]
W, H, SEED = (pos[2:5] + ["1024", "1024", "42"][len(pos[2:5]):])
dtypes, timing = {}, {}

BASELINE = "--baseline" in sys.argv  # disable every numeric patch: production fp32 behaviour, same harness
orig_te = TE.TimestepEmbedder.__call__
if not BASELINE:
  TE.TimestepEmbedder.__call__ = lambda self, *a, **k: orig_te(self, *a, **k).astype(mx.bfloat16)
orig_attn = A.ZImageAttention.__call__
def attn(self, hidden_states, *a, **k):
    dtypes.setdefault("attention_input", set()).add(str(hidden_states.dtype)); return orig_attn(self, hidden_states, *a, **k)
A.ZImageAttention.__call__ = attn
ROPE_CAST = "--rope-cast" in sys.argv and not BASELINE
if ROPE_CAST:  # diffusers semantics: rotary math in fp32 tables, result cast back to the input dtype
    orig_rope = A.ZImageAttention._apply_rotary_emb
    A.ZImageAttention._apply_rotary_emb = staticmethod(lambda x, f: orig_rope(x, f).astype(x.dtype))
orig_sdpa = A.scaled_dot_product_attention
def sdpa(q, k, v, scale=None, mask=None):
    dtypes.setdefault("sdpa_q", set()).add(str(q.dtype))
    return orig_sdpa(q, k, v, scale=scale, mask=mask if (BASELINE or mask is None) else mask.astype(q.dtype))
A.scaled_dot_product_attention = sdpa
from mflux.models.z_image.model.z_image_transformer import feed_forward as FF
orig_ff = FF.FeedForward.__call__
def ff(self, x):
    dtypes.setdefault("ffn_input", set()).add(str(x.dtype)); return orig_ff(self, x)
FF.FeedForward.__call__ = ff
orig_init = zmod.ZImage.__init__
def init(self, *a, **k):
    orig_init(self, *a, **k)
    if BASELINE: return
    t = self.transformer
    t.x_pad_token = t.x_pad_token.astype(mx.bfloat16); t.cap_pad_token = t.cap_pad_token.astype(mx.bfloat16)
zmod.ZImage.__init__ = init
for name in ("_encode_prompts", "_decode_latents", "generate_image"):
    fn = getattr(zmod.ZImage, name)
    def wrap(fn=fn, name=name):
        def w(self, *a, **k):
            mx.synchronize(); s = time.perf_counter(); r = fn(self, *a, **k); mx.synchronize()
            timing[name] = round(time.perf_counter() - s, 3); return r
        return w
    setattr(zmod.ZImage, name, wrap())
sys.argv = ["mflux-generate-z-image-turbo", "--model", sys.argv[0].rsplit("/research/", 1)[0] + "/models/mflux/z-image-turbo-mflux-q4",
            "--base-model", "z-image-turbo", f"--prompt={prompt}", "--width", W, "--height", H, "--steps", "9",
            "--seed", SEED, "--low-ram", "--output", out]
cli.main()
timing["denoise"] = round(timing["generate_image"] - timing["_encode_prompts"] - timing["_decode_latents"], 3)
print("E02RESULT " + json.dumps({"baseline": BASELINE, "rope_cast": ROPE_CAST, "dtypes": {k: sorted(v) for k, v in dtypes.items()}, "timing": timing, "peak_mlx_gb": round(mx.get_peak_memory() / 1e9, 3)}))
