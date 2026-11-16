from __future__ import annotations

import asyncio
from io import BytesIO
from types import SimpleNamespace

from fastapi import UploadFile

from webapp import community_app


def test_analyze_passes_spooled_upload_file_without_materializing_bytes(monkeypatch) -> None:
    user = SimpleNamespace(id="guest-1", email=None, guest=True)
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        community_app, "authenticate_optional", lambda _request: user
    )

    async def fake_run_in_threadpool(func, *args, **kwargs):
        captured["func"] = func
        captured["args"] = args
        captured["kwargs"] = kwargs
        return "job-streamed"

    monkeypatch.setattr(community_app, "run_in_threadpool", fake_run_in_threadpool)
    upload = UploadFile(filename="sample.tif", file=BytesIO(b"uint16-image"))
    upload.file.seek(5)

    result = asyncio.run(
        community_app.analyze(
            object(),
            upload,
            False,
            "auto",
            "nuclei,morphology,intensity",
            0,
            0,
            0,
            0,
        )
    )

    assert captured["func"] is community_app.create_job
    assert captured["args"][0] is upload.file
    assert upload.file.tell() == 0
    assert result["job_id"] == "job-streamed"
    assert result["research_consent"] is False
