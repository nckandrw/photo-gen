"""E10: which code paths actually promote the Z-Image DiT hidden stream to float32? (verification for the upstream issue)
One variant per process: applies a subset of the E02 casts, runs a tiny generation (256², 2 steps, --low-ram), and
records runtime dtypes: pad tokens after weight load, TimestepEmbedder output, RoPE output, SDPA q, FFN input.
Variants: none | pad | temb | rope | temb+rope | pad+temb+rope
Usage: e10_promotion_ablation.py <variant> <out.json>"""
import json, os, sys
variant, out = sys.argv[1], sys.argv[2]
parts = set() if variant == "none" else set(variant.split("+"))
import mlx.core as mx  # noqa: E402
import mflux.models.z_image.variants.z_image as zmod  # noqa: E402
from mflux.models.z_image.model.z_image_transformer import attention as AT, timestep_embedder as TE, feed_forward as FF  # noqa: E402
from mflux.models.z_image.cli import z_image_turbo_generate as cli  # noqa: E402

seen = {}
def note(k, x): seen.setdefault(k, str(x.dtype))

o_te = TE.TimestepEmbedder.__call__
def te(self, *a, **k):
    y = o_te(self, *a, **k); note("timestep_embedder.out(raw)", y)
    return y.astype(mx.bfloat16) if "temb" in parts else y
TE.TimestepEmbedder.__call__ = te
o_rope = AT.ZImageAttention._apply_rotary_emb
def rope(x, f):
    note("rope.in", x); note("rope.freqs", f); y = o_rope(x, f); note("rope.out(raw)", y)
    return y.astype(x.dtype) if "rope" in parts else y
AT.ZImageAttention._apply_rotary_emb = staticmethod(rope)
o_sdpa = AT.scaled_dot_product_attention
def sdpa(q, k, v, scale=None, mask=None):
    note("sdpa.q", q)
    if mask is not None and q.dtype == mx.bfloat16: mask = mask.astype(q.dtype)
    return o_sdpa(q, k, v, scale=scale, mask=mask)
AT.scaled_dot_product_attention = sdpa
o_ff = FF.FeedForward.__call__
def ff(self, x): note("ffn.in", x); return o_ff(self, x)
FF.FeedForward.__call__ = ff
o_init = zmod.ZImage.__init__
def init(self, *a, **k):
    o_init(self, *a, **k)
    t = self.transformer
    seen["x_pad_token(after load)"] = str(t.x_pad_token.dtype); seen["cap_pad_token(after load)"] = str(t.cap_pad_token.dtype)
    if "pad" in parts:
        t.x_pad_token = t.x_pad_token.astype(mx.bfloat16); t.cap_pad_token = t.cap_pad_token.astype(mx.bfloat16)
zmod.ZImage.__init__ = init
root = os.path.expanduser("~/Dev/photo-gen")
sys.argv = ["mflux-generate-z-image-turbo", "--model", f"{root}/models/mflux/z-image-turbo-mflux-q4", "--base-model",
            "z-image-turbo", "--prompt=a red apple on a wooden table", "--width", "256", "--height", "256", "--steps", "2",
            "--seed", "42", "--low-ram", "--output", f"{os.path.dirname(os.path.abspath(out))}/e10-{variant}.png"]
cli.main()
json.dump({"variant": variant, "dtypes": seen}, open(out, "w"), indent=1)
print(json.dumps({"variant": variant, "dtypes": seen}))
