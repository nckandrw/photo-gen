"""Protects the production transformer-lifetime fix (research/experiments/production-memory-fix-report.md).

Runs against the real mflux 0.20.0 classes in a subprocess (the fix patches classes process-wide), with a tiny
stand-in object as the "transformer": no model weights are loaded and no GPU work is done.
"""
import json
import subprocess
import sys
import unittest

PROBE = r'''
import gc, json, sys, types, weakref
import mlx.core as mx
from photogen.runtimes import mflux_zimage_worker as W
import mflux.models.z_image.variants.z_image as zmod
from mflux.callbacks.instances.memory_saver import MemorySaver

release = sys.argv[1] == "1"
status = W._install_transformer_release(mx) if release else None

class FakeTransformer:  # stands in for the ~3.47 GB q4 DiT
    pass

t = FakeTransformer()
ref = weakref.ref(t)
model = types.SimpleNamespace(transformer=t, tiling_config=None)
predict = zmod.ZImage._predict(model.transformer)   # what generate_image holds in its local `predict`
del t
saver = MemorySaver(model=model, keep_transformer=False, cache_limit_bytes=None)
saver.call_after_loop(seed=0, prompt="x", latents=None, config=None)   # --low-ram path: model.transformer = None
gc.collect()
print(json.dumps({"model_attr_cleared": model.transformer is None, "alive_while_predict_held": ref() is not None,
                  "status": status}))
'''


def run(release: bool) -> dict:
    p = subprocess.run([sys.executable, "-c", PROBE, "1" if release else "0"], capture_output=True, text=True,
                       timeout=300)
    if p.returncode != 0:
        raise AssertionError(p.stderr[-2000:])
    return json.loads(p.stdout.strip().splitlines()[-1])


class TransformerLifetimeTests(unittest.TestCase):
    def test_upstream_behaviour_retains_transformer(self):
        """Documents the bug: without the fix, the compiled predict closure keeps the transformer alive
        after MemorySaver drops model.transformer. If this starts failing, upstream fixed it — re-evaluate."""
        r = run(release=False)
        self.assertTrue(r["model_attr_cleared"])
        self.assertTrue(r["alive_while_predict_held"])

    def test_fix_makes_transformer_reclaimable(self):
        r = run(release=True)
        self.assertTrue(r["model_attr_cleared"])
        self.assertFalse(r["alive_while_predict_held"], "transformer still reachable after call_after_loop")
        self.assertEqual(r["status"], {"installed": True, "released": True})


if __name__ == "__main__":
    unittest.main()
