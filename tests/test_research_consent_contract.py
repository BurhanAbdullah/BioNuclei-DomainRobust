from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from webapp import community_app


def test_analyze_rejects_unimplemented_research_consent(monkeypatch):
    def unexpected_call(*_args, **_kwargs):
        pytest.fail("unsupported research consent must be rejected before creating or authenticating a job")

    monkeypatch.setattr(community_app, "authenticate_optional", unexpected_call)
    monkeypatch.setattr(community_app, "create_job", unexpected_call)

    with TestClient(community_app.app) as client:
        response = client.post(
            "/analyze",
            data={"research_consent": "true"},
            files={"image": ("sample.tif", b"not-read", "image/tiff")},
        )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Research retention is not implemented; uploads are processed transiently and are not used for training."
    )
