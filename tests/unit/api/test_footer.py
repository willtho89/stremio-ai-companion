import re
from starlette.testclient import TestClient
from app.api import app

client = TestClient(app)

def test_footer_visible_by_default(monkeypatch):
    response = client.get("/")
    assert response.status_code == 200
    html = response.text
    assert re.search(r">v?\d+\.\d+\.\d+<", html)
    assert "GitHub" in html
    assert "Buy me a coffee" in html


def test_footer_can_be_disabled(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.FOOTER_ENABLED", False)
    response = client.get("/")
    assert response.status_code == 200
    html = response.text
    assert "Buy me a coffee" not in html
