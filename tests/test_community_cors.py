from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

from webapp.community_app import PUBLIC_SITE_ORIGIN, _configured_origins


def test_public_pages_origin_survives_restricted_origin_configuration() -> None:
    origins = _configured_origins("https://internal.example")
    assert origins == ["https://internal.example", PUBLIC_SITE_ORIGIN]

    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["*"],
    )

    @app.post("/analyze")
    def analyze() -> dict[str, bool]:
        return {"accepted": True}

    headers = {
        "Origin": PUBLIC_SITE_ORIGIN,
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "x-bionuclei-guest-token,content-type",
    }
    with TestClient(app) as client:
        preflight = client.options("/analyze", headers=headers)
        assert preflight.status_code == 200, preflight.text
        assert preflight.headers["access-control-allow-origin"] == PUBLIC_SITE_ORIGIN
        assert "x-bionuclei-guest-token" in preflight.headers[
            "access-control-allow-headers"
        ].lower()

        response = client.post(
            "/analyze",
            headers={
                "Origin": PUBLIC_SITE_ORIGIN,
                "X-BioNuclei-Guest-Token": "test-only-token",
            },
            json={},
        )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == PUBLIC_SITE_ORIGIN


def test_empty_origin_configuration_keeps_only_the_public_ui_origin() -> None:
    assert _configured_origins("") == [PUBLIC_SITE_ORIGIN]


def test_wildcard_mode_remains_available_without_credentials() -> None:
    assert _configured_origins("*") == ["*"]
