from pathlib import Path

from fastapi.testclient import TestClient

from verify.negotiation import web


def test_root_prefers_built_ui_bundle(monkeypatch, tmp_path):
    static_dir = tmp_path / "static"
    built_dir = static_dir / "ui"
    static_dir.mkdir()
    built_dir.mkdir()
    (static_dir / "index.html").write_text("<html><body>legacy-ui</body></html>")
    (built_dir / "index.html").write_text("<html><body>react-ui</body></html>")

    monkeypatch.setattr(web, "STATIC_DIR", static_dir)

    client = TestClient(web.app)
    response = client.get("/")

    assert response.status_code == 200
    assert "react-ui" in response.text


def test_api_routes_remain_available_when_ui_bundle_exists(monkeypatch, tmp_path):
    static_dir = tmp_path / "static"
    built_dir = static_dir / "ui"
    static_dir.mkdir()
    built_dir.mkdir()
    (static_dir / "index.html").write_text("<html><body>legacy-ui</body></html>")
    (built_dir / "index.html").write_text("<html><body>react-ui</body></html>")

    monkeypatch.setattr(web, "STATIC_DIR", static_dir)

    client = TestClient(web.app)
    response = client.get("/api/skills")

    assert response.status_code == 200
    assert isinstance(response.json(), list)
