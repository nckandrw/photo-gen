"""E01: record the actual activation dtypes flowing through the production Z-Image DiT (mflux 0.20.0, q4 pack).
Read-only probe: wraps attention/FFN/linear __call__ to log input dtypes once; tiny 256x256, 2-step run."""
import collections, json, os
import mlx.core as mx
from mflux.models.common.config import ModelConfig
from mflux.models.z_image.variants.z_image import ZImage
from mflux.models.z_image.model.z_image_transformer import attention as A, feed_forward as F, transformer as T

seen = collections.OrderedDict()
def probe(name, cls):
    orig = cls.__call__
    def wrapped(self, *a, **k):
        first = a[0] if a else next(iter(k.values()))
        if name not in seen and isinstance(first, mx.array):
            seen[name] = str(first.dtype)
        return orig(self, *a, **k)
    cls.__call__ = wrapped
probe("ZImageAttention.input(hidden_states)", A.ZImageAttention)
probe("FeedForward.input", F.FeedForward)
orig_t = T.ZImageTransformer.__call__
def t_wrapped(self, x, timestep, sigmas, cap_feats, **k):
    seen.setdefault("transformer.x(latents)", str(x.dtype)); seen.setdefault("transformer.cap_feats", str(cap_feats.dtype))
    out = orig_t(self, x, timestep, sigmas, cap_feats, **k); seen.setdefault("transformer.output", str(out.dtype)); return out
T.ZImageTransformer.__call__ = t_wrapped
orig_sdpa = A.scaled_dot_product_attention
def sdpa_probe(q, k, v, scale=None, mask=None):
    seen.setdefault("sdpa.q", str(q.dtype)); seen.setdefault("sdpa.mask", str(mask.dtype) if mask is not None else "None")
    return orig_sdpa(q, k, v, scale=scale, mask=mask)
A.scaled_dot_product_attention = sdpa_probe

root = os.path.expanduser("~/Dev/photo-gen")
m = ZImage(model_config=ModelConfig.z_image_turbo(), model_path=f"{root}/models/mflux/z-image-turbo-mflux-q4")
seen["model.precision(ModelConfig)"] = str(ModelConfig.precision)
w = m.transformer.layers[0].attention.to_q
seen["to_q.layer_type"] = type(w).__name__
seen["to_q.scales.dtype"] = str(getattr(w, "scales", mx.array(0)).dtype)
m.generate_image(seed=1, prompt="probe", num_inference_steps=2, width=256, height=256)
print(json.dumps(seen, indent=1))
