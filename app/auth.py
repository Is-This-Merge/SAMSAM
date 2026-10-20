from functools import wraps
from datetime import datetime
import secrets
from urllib.parse import urljoin, urlparse

from authlib.integrations.flask_client import OAuth
from flask import (
    Blueprint,
    current_app,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from sqlalchemy import select

from .db import db
from .models import User


bp = Blueprint("auth", __name__, url_prefix="/auth")
oauth = OAuth()


def init_oauth(app):
    oauth.init_app(app)
    if app.config["GOOGLE_OAUTH_CONFIGURED"]:
        oauth.register(
            name="google",
            client_id=app.config["GOOGLE_CLIENT_ID"],
            client_secret=app.config["GOOGLE_CLIENT_SECRET"],
            server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
            client_kwargs={"scope": "openid email profile"},
        )


def _safe_next_url(value):
    if not value:
        return None
    host_url = request.host_url
    target = urlparse(urljoin(host_url, value))
    host = urlparse(host_url)
    if target.scheme in {"http", "https"} and target.netloc == host.netloc:
        return target.path + (f"?{target.query}" if target.query else "")
    return None


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            if request.path.startswith("/api/"):
                return jsonify(error="authentication_required"), 401
            return redirect(url_for("auth.login_page", next=request.full_path.rstrip("?")))
        return view(*args, **kwargs)

    return wrapped


@bp.before_app_request
def load_logged_in_user():
    user_id = session.get("user_id")
    g.user = db.session.get(User, user_id) if user_id else None
    if user_id and g.user is None:
        session.clear()
    if g.user is not None and "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)


@bp.before_app_request
def protect_authenticated_mutations():
    if g.user is None or request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
        return None
    supplied = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token")
    if not supplied or not secrets.compare_digest(supplied, session.get("csrf_token", "")):
        return jsonify(error="invalid_csrf_token"), 403
    return None


@bp.app_context_processor
def inject_current_user():
    return {"current_user": g.get("user"), "current_year": datetime.now().year}


@bp.get("/login")
def login_page():
    return render_template(
        "login.html",
        oauth_configured=current_app.config["GOOGLE_OAUTH_CONFIGURED"],
        next_url=_safe_next_url(request.args.get("next")),
    )


@bp.get("/google")
def google_login():
    if not current_app.config["GOOGLE_OAUTH_CONFIGURED"]:
        flash("Google OAuth 환경변수가 아직 설정되지 않았습니다.", "error")
        return redirect(url_for("auth.login_page"))
    next_url = _safe_next_url(request.args.get("next"))
    if next_url:
        session["login_next"] = next_url
    redirect_uri = current_app.config.get("GOOGLE_REDIRECT_URI") or url_for(
        "auth.google_callback", _external=True
    )
    try:
        return oauth.google.authorize_redirect(redirect_uri)
    except Exception:
        current_app.logger.exception("Failed to start Google OAuth")
        flash("Google 로그인 서버에 연결하지 못했습니다. 잠시 후 다시 시도해 주세요.", "error")
        return redirect(url_for("auth.login_page"))


@bp.get("/callback")
def google_callback():
    if not current_app.config["GOOGLE_OAUTH_CONFIGURED"]:
        return redirect(url_for("auth.login_page"))
    try:
        token = oauth.google.authorize_access_token()
    except Exception:
        current_app.logger.exception("Google OAuth callback failed")
        flash("Google 인증을 완료하지 못했습니다. callback 주소와 OAuth 설정을 확인해 주세요.", "error")
        return redirect(url_for("auth.login_page"))
    profile = token.get("userinfo")
    if not profile or not profile.get("sub") or not profile.get("email_verified"):
        flash("검증된 Google 계정 정보를 확인하지 못했습니다.", "error")
        return redirect(url_for("auth.login_page"))

    user = db.session.scalar(select(User).where(User.google_sub == profile["sub"]))
    if user is None:
        user = User(google_sub=profile["sub"], email=profile["email"])
        db.session.add(user)
    user.email = profile["email"]
    user.display_name = profile.get("name") or profile["email"].split("@", 1)[0]
    user.picture_url = profile.get("picture", "")
    db.session.commit()

    next_url = session.get("login_next")
    session.clear()
    session["user_id"] = user.id
    return redirect(next_url or url_for("main.index"))


@bp.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("main.index"))
