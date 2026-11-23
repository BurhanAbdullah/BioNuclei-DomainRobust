import json
import os
import signal
import socket
import subprocess
import sys
import tarfile
import time
import urllib.request
from pathlib import Path

import numpy as np
import pytest
import tifffile

ROOT = Path(__file__).resolve().parents[1]


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _get(url, data=None, headers=None, timeout=10):
    req = urllib.request.Request(url, data=data, headers=headers or {}, method="POST" if data is not None else "GET")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read()


def _multipart(path: Path):
    boundary = "----bionuclei-test"
    body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"image\"; filename=\"{path.name}\"\r\nContent-Type: image/tiff\r\n\r\n").encode() + path.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
    return body, {"Content-Type": f"multipart/form-data; boundary={boundary}"}


@pytest.fixture(scope="module")
def checkpoint(tmp_path_factory):
    torch = pytest.importorskip("torch")
    from bionuclei.models import BoundaryUNet
    torch.manual_seed(0)
    path = tmp_path_factory.mktemp("ckpt") / "model.pt"
    torch.save({"config": {"model": {"in_channels": 1, "out_channels": 3, "base_channels": 8}}, "model": BoundaryUNet(in_channels=1, out_channels=3, base_channels=8).state_dict()}, path)
    return path


def test_run_local_serves_site_and_api_and_saves_results_locally(tmp_path, checkpoint):
    api_port, site_port = _free_port(), _free_port()
    data, key_file = tmp_path / "data", tmp_path / "keys" / "data.key"
    proc = subprocess.Popen([sys.executable, str(ROOT / "scripts" / "run_local.py"), "--checkpoint", str(checkpoint), "--data", str(data),
                             "--key-file", str(key_file), "--api-port", str(api_port), "--site-port", str(site_port), "--no-browser", "--keep-days", "30"],
                            cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        site, api = f"http://127.0.0.1:{site_port}", f"http://127.0.0.1:{api_port}"
        deadline = time.time() + 120
        while time.time() < deadline:
            try:
                _get(f"{api}/health", timeout=2)
                _get(f"{site}/index.html", timeout=2)
                break
            except Exception:
                time.sleep(0.5)
        status, cfg = _get(f"{site}/assets/bionuclei-config.js")
        assert status == 200 and api.encode() in cfg and b"onrender.com" not in cfg
        health = json.loads(_get(f"{api}/health")[1])
        assert health["checkpoint_available"] and health["result_retention_hours"] == 720
        with pytest.raises(urllib.error.HTTPError):
            _get(f"{site}/assets/")  # no folder listings

        token = json.loads(_get(f"{api}/guest-session", data=b"")[1])["guest_token"]
        rng = np.random.default_rng(3)
        img = rng.normal(250, 20, (128, 128))
        yy, xx = np.mgrid[:128, :128]
        for cy, cx in [(30, 30), (90, 40), (60, 100)]:
            img += 3000 * np.exp(-((yy - cy) ** 2 + (xx - cx) ** 2) / 60.0)
        sample = tmp_path / "sample.tif"
        tifffile.imwrite(sample, img.clip(0, 65535).astype(np.uint16))
        body, headers = _multipart(sample)
        job = json.loads(_get(f"{api}/analyze", data=body, headers={**headers, "X-BioNuclei-Guest-Token": token})[1])["job_id"]
        state = ""
        for _ in range(240):
            state = json.loads(_get(f"{api}/jobs/{job}", headers={"X-BioNuclei-Guest-Token": token})[1])["status"].lower()
            if state in {"completed", "failed"}:
                break
            time.sleep(0.5)
        assert state == "completed"
        assert (data / "jobs").is_dir() and any((data / "jobs").rglob("analysis_report.pdf"))
        assert key_file.is_file() and oct(key_file.stat().st_mode & 0o777) == "0o600"
    finally:
        proc.send_signal(signal.SIGINT)
        try:
            proc.wait(timeout=20)
        except subprocess.TimeoutExpired:
            proc.kill()

    backups = tmp_path / "backups"
    from bionuclei.storage import Owner, SecureStore, _decode_key
    SecureStore(data, _decode_key(key_file.read_text().strip())).write_bytes(Owner("user", "3f1c2a9e-7b44-4d8e-9a10-2b6f0c1d5e77"), "reports", "r.json", b"kept")
    out = subprocess.run([sys.executable, str(ROOT / "scripts" / "run_local.py"), "--data", str(data), "--key-file", str(key_file), "--backup", str(backups)],
                         cwd=ROOT, capture_output=True, text=True, timeout=60)
    assert out.returncode == 0, out.stderr
    assert "all verified" in out.stdout
    archive = next(backups.glob("bionuclei-backup-*.tar.gz"))
    with tarfile.open(archive) as tar:
        assert b"kept" not in b"".join(tar.extractfile(m).read() for m in tar.getmembers() if m.isfile())


def test_run_local_needs_a_checkpoint(tmp_path):
    out = subprocess.run([sys.executable, str(ROOT / "scripts" / "run_local.py"), "--data", str(tmp_path / "d"), "--key-file", str(tmp_path / "k"), "--no-browser"],
                         cwd=ROOT, capture_output=True, text=True, timeout=60, env={k: v for k, v in os.environ.items() if k != "BIONUCLEI_CHECKPOINT"})
    assert out.returncode == 2 and "checkpoint is required" in out.stderr
