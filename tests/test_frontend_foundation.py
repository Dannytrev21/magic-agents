"""TDD coverage for the frontend foundation contract."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from verify.negotiation import web


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("LLM_MOCK", "true")
    web._session.clear()
    return TestClient(web.app)


def test_root_falls_back_to_legacy_frontend_when_bundle_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    monkeypatch.setattr(web, "UI_DIST_DIR", tmp_path / "missing-dist", raising=False)

    response = client.get("/")

    assert response.status_code == 200
    assert "Jira Stories In Progress" in response.text


def test_root_serves_compiled_frontend_and_assets_when_bundle_exists(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    ui_dist = tmp_path / "ui" / "dist"
    assets_dir = ui_dist / "assets"
    assets_dir.mkdir(parents=True)
    (ui_dist / "index.html").write_text(
        """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>Magic Agents Workspace</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/assets/app-main.js"></script>
  </body>
</html>
"""
    )
    (assets_dir / "app-main.js").write_text("console.log('workspace-ready');")
    monkeypatch.setattr(web, "UI_DIST_DIR", ui_dist, raising=False)

    response = client.get("/")
    asset_response = client.get("/assets/app-main.js")
    api_response = client.get("/api/jira/configured")

    assert response.status_code == 200
    assert "Magic Agents Workspace" in response.text
    assert asset_response.status_code == 200
    assert "workspace-ready" in asset_response.text
    assert api_response.status_code == 200
    assert api_response.json() == {"configured": False}
