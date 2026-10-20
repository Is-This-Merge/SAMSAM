from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from config import Config
from .auth import init_oauth
from .db import init_db
from .assets import init_assets


def create_app(test_config=None):
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
        static_url_path="/src",
    )
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)

    # Render 프록시 뒤에서도 OAuth callback URL을 원래 HTTPS 주소로 생성한다.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

    init_db(app)
    init_assets(app)
    init_oauth(app)

    from .seed import seed_samples_command
    app.cli.add_command(seed_samples_command)

    # Import models before Flask-Migrate inspects SQLAlchemy metadata.
    from . import models  # noqa: F401

    from .views import main_views
    from .views import quiz_views
    from .views import profile_views
    from . import auth
    app.register_blueprint(auth.bp)
    app.register_blueprint(main_views.bp)
    app.register_blueprint(quiz_views.bp)
    app.register_blueprint(profile_views.bp)
    from .views import study_views
    app.register_blueprint(study_views.bp)

    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        return response

    return app
