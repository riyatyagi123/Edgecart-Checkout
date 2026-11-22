"""Shared helpers for the training scripts (paths are relative to this folder)."""
import sys
from pathlib import Path

TRAIN_DIR = Path(__file__).resolve().parent
ROOT = TRAIN_DIR.parent
sys.path.insert(0, str(ROOT))
import vision.torch_compat  # noqa: E402,F401  (torch>=2.6 checkpoint loading)

import torch  # noqa: E402

DEVICE = "0" if torch.cuda.is_available() else "cpu"
RUNS_DIR = TRAIN_DIR / "runs"
CUSTOM_DATASET = TRAIN_DIR / "custom_dataset"


def resolve_data(yaml_path) -> str:
    """Return a dataset YAML whose 'path' is absolute (ultralytics would otherwise
    resolve relative paths against its global datasets_dir, not this folder)."""
    import yaml
    yaml_path = Path(yaml_path).resolve()
    cfg = yaml.safe_load(yaml_path.read_text()) or {}
    p = Path(cfg.get("path", "."))
    if p.is_absolute():
        return str(yaml_path)
    cfg["path"] = str((yaml_path.parent / p).resolve())
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    out = RUNS_DIR / f"_resolved_{yaml_path.name}"
    out.write_text(yaml.safe_dump(cfg, sort_keys=False))
    return str(out)
