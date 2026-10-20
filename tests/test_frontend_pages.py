import re
from pathlib import Path
from urllib.parse import urlsplit

import pytest


@pytest.mark.parametrize("url", ["/", "/quiz.html", "/study.html", "/create.html", "/inventory.html", "/mypage.html", "/info.html", "/match.html", "/mistakes.html"])
def test_pages_render_with_resolvable_versioned_assets(client, url):
    response = client.get(url)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assets = re.findall(r'(?:src|href)="(/src/[^"\s]+)"', html)
    assert assets
    for asset in assets:
        result = client.get(asset)
        assert result.status_code == 200, asset
        if urlsplit(asset).path.endswith((".css", ".js")):
            assert "v=" in asset
            assert "no-cache" in result.headers["Cache-Control"]
    assert html.index("styles/var.css") < html.index("styles/common.css")


def test_browser_module_dependencies_resolve_inside_static_directory():
    root = (Path(__file__).parents[1] / "app/static").resolve()
    for module in root.rglob("*.js"):
        for dependency in re.findall(r"(?:from\s+|import\s*)['\"](\.[^'\"]+)['\"]", module.read_text(encoding="utf-8")):
            target = (module.parent / dependency).resolve()
            assert target.is_relative_to(root)
            assert target.is_file(), (module, dependency)
