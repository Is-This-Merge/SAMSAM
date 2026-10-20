"""Version template assets automatically and revalidate module dependencies."""

from pathlib import Path

from flask import request, url_for


def init_assets(app):
    def asset_url(filename):
        path = Path(app.static_folder) / filename
        version = path.stat().st_mtime_ns if path.is_file() else 0
        return url_for("static", filename=filename, v=version)

    app.jinja_env.globals["asset_url"] = asset_url

    @app.after_request
    def revalidate_code_assets(response):
        if request.endpoint == "static" and request.path.endswith((".js", ".css")):
            response.cache_control.no_cache = True
        return response
