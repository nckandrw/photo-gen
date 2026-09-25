"""Research-only sigma schedules for the sigma-schedule audit (sigma-schedule-audit.md).

Loaded by mflux through its own external-scheduler hook (`--scheduler sigma_sched.<Class>`, see
mflux/models/common/schedulers/__init__.py::try_import_external_scheduler). No mflux file is modified.

Both classes subclass mflux's LinearScheduler and override ONLY `_get_sigmas`, so `step()` and the
timesteps (0..N-1 indices; the model receives 1 - sigma) are byte-identical to the default path.
Neither defines `set_image_seq_len`, so Config.scheduler never re-derives the sigmas.

- MfluxDynamicControl: re-implements mflux's own resolution-dependent shift (plumbing-parity control:
  must reproduce the production pixel hashes exactly).
- OfficialStatic3: the official Z-Image-Turbo schedule (scheduler_config.json: use_dynamic_shifting=false,
  shift=3.0): sigma' = 3 s / (1 + 2 s), independent of resolution.

If SIGMA_DUMP is set, the sigmas actually used are written there as JSON (arm verification).
"""
import json
import os

import mlx.core as mx
from mflux.models.common.schedulers.linear_scheduler import LinearScheduler


def _base(n):
    s = mx.linspace(1.0, 1.0 / n, n)
    return mx.array(s).astype(mx.float32)


def _dump(name, sigmas, extra):
    p = os.environ.get("SIGMA_DUMP")
    if p:
        json.dump({"scheduler": name, "sigmas": [float(x) for x in sigmas.tolist()], **extra}, open(p, "w"))


class MfluxDynamicControl(LinearScheduler):
    def _get_sigmas(self):
        mc, n = self.config.model_config, self.config.num_inference_steps
        s = _base(n)
        m = (mc.sigma_max_shift - mc.sigma_base_shift) / (mc.sigma_max_seq_len - mc.sigma_base_seq_len)
        b = mc.sigma_base_shift - m * mc.sigma_base_seq_len
        mu = mx.array(m * self.config.width * self.config.height / 256 + b)
        shifted = mx.exp(mu) / (mx.exp(mu) + (1 / s - 1))
        assert mc.sigma_shift_terminal is None  # z-image-turbo in mflux 0.20.0
        out = mx.concatenate([shifted, mx.zeros(1)])
        _dump("MfluxDynamicControl", out, {"exp_mu": float(mx.exp(mu).item())})
        return out


class OfficialStatic3(LinearScheduler):
    SHIFT = 3.0

    def _get_sigmas(self):
        s = _base(self.config.num_inference_steps)
        shifted = self.SHIFT * s / (1 + (self.SHIFT - 1) * s)
        out = mx.concatenate([shifted, mx.zeros(1)])
        _dump("OfficialStatic3", out, {"shift": self.SHIFT})
        return out
