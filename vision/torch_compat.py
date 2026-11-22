"""PyTorch >= 2.6 defaults torch.load(weights_only=True), which breaks older
YOLO / CLIP checkpoints. Both original repos patched this in every script;
it now lives in one place and is imported by the vision package."""
import torch

if not getattr(torch.load, "_grab_and_go_patched", False):
    _orig_load = torch.load

    def _patched_load(*args, **kwargs):
        kwargs.setdefault("weights_only", False)
        return _orig_load(*args, **kwargs)

    _patched_load._grab_and_go_patched = True
    torch.load = _patched_load
