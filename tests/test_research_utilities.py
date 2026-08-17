from __future__ import annotations

import json
from pathlib import Path

from scripts.bootstrap_metrics import main as bootstrap_main


def test_bootstrap_metrics_is_image_level(monkeypatch, tmp_path: Path) -> None:
    metrics = {
        "per_image": [
            {"dice": 0.5, "iou": 0.4, "aji": 0.3, "boundary_f1": 0.2},
            {"dice": 0.7, "iou": 0.6, "aji": 0.5, "boundary_f1": 0.4},
            {"dice": 0.9, "iou": 0.8, "aji": 0.7, "boundary_f1": 0.6},
        ]
    }
    src = tmp_path / "metrics.json"
    out = tmp_path / "ci.json"
    src.write_text(json.dumps(metrics))
    monkeypatch.setattr(
        "sys.argv",
        ["bootstrap_metrics.py", "--metrics", str(src), "--output", str(out), "--iterations", "100", "--seed", "42"],
    )
    bootstrap_main()
    result = json.loads(out.read_text())
    assert result["n_images"] == 3
    assert result["resampling_unit"] == "image"
    assert set(result["metrics"]) == {"dice", "iou", "aji", "boundary_f1"}
