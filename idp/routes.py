"""OAuth2 인증 라우트. SOLID-SRP: HTTP 요청/응답 처리만 담당."""
from urllib.parse import urlencode

from flask import (
    Blueprint, render_template, request, redirect, session, url_for, flash,
    current_app
)
from flask_login import current_user, login_user, logout_user

from idp.models import db, OAuth2Client
from idp.repositories.user_repo import UserRepository
from idp.repositories.oauth_repo import OAuthRepository
from idp.services.user_service import UserService
from idp.services.oauth_service import OAuthService

auth_bp = Blueprint("auth", __name__)


def _get_services():
    user_repo = UserRepository()
    oauth_repo = OAuthRepository()
    user_service = UserService(user_repo)
    oauth_service = OAuthService(oauth_repo, user_repo)
    return user_service, oauth_service


@auth_bp.route("/")
def index():
    if current_user.is_authenticated:
        return render_template(
            "index.html",
            user=current_user,
            app_title=current_app.config["APP_TITLE"]
        )
    return render_template(
        "login.html",
        app_title=current_app.config["APP_TITLE"],
    )


@auth_bp.route("/oauth/authorize", methods=["GET", "POST"])
def authorize():
    user_service, oauth_service = _get_services()

    current_app.logger.info(f"Authorize request ({request.method}) from {request.remote_addr}")

    # 파라미터 획득 (GET과 POST 모두 지원)
    client_id = request.args.get("client_id") or request.form.get("client_id", "")
    redirect_uri = request.args.get("redirect_uri") or request.form.get("redirect_uri", "")
    response_type = request.args.get("response_type") or request.form.get("response_type", "")
    scope = request.args.get("scope") or request.form.get("scope", "openid profile email")
    state = request.args.get("state") or request.form.get("state", "")

    if request.method == "GET":
        if current_user.is_authenticated:
            # SSO Logic: 자동 리다이렉트 전 랜딩 페이지를 거쳐 브라우저가 앱 쿠키를 저장할 시간을 줌
            try:
                oauth_service.validate_authorize_request(
                    client_id, redirect_uri, response_type
                )
                code = oauth_service.create_authorization_code(
                    client_id=client_id,
                    redirect_uri=redirect_uri,
                    scope=scope,
                    user_id=current_user.id,
                )
                params = {"code": code.code}
                if state:
                    params["state"] = state
                
                target_url = f"{redirect_uri}?{urlencode(params)}"
                current_app.logger.info(f"SSO: Showing landing page for user {current_user.username}")
                
                # 원활한 이동을 위해 1초 대기 후 이동하는 랜딩 페이지 반환
                return render_template(
                    "sso_landing.html",
                    target_url=target_url,
                    username=current_user.username,
                    app_title=current_app.config["APP_TITLE"]
                )
            except ValueError as e:
                current_app.logger.warning(f"SSO Validation failed: {str(e)}")
                # Validation failed, show login form instead (fallback)
                pass

        # 로그인 페이지 표시
        try:
            oauth_service.validate_authorize_request(
                client_id, redirect_uri, response_type
            )
        except ValueError as e:
            return render_template("login.html", error=str(e),
                                   app_title=current_app.config["APP_TITLE"]), 400
        return render_template(
            "login.html",
            client_id=client_id,
            redirect_uri=redirect_uri,
            response_type=response_type,
            scope=scope,
            state=state,
            app_title=current_app.config["APP_TITLE"],
        )

    # POST: 로그인 처리
    username = request.form.get("username", "")
    password = request.form.get("password", "")

    user = user_service.authenticate(username, password)
    if not user:
        return render_template(
            "login.html",
            error="Invalid username or password",
            client_id=client_id,
            redirect_uri=redirect_uri,
            response_type=response_type,
            scope=scope,
            state=state,
            app_title=current_app.config["APP_TITLE"],
        ), 401

    # 로그인 세션 생성 및 Authorization Code 발급
    login_user(user)
    try:
        oauth_service.validate_authorize_request(client_id, redirect_uri, response_type)
        code = oauth_service.create_authorization_code(
            client_id=client_id,
            redirect_uri=redirect_uri,
            scope=scope,
            user_id=user.id,
        )
    except Exception as e:
        return render_template("login.html", error=str(e),
                               client_id=client_id,
                               redirect_uri=redirect_uri,
                               app_title=current_app.config["APP_TITLE"]), 500

    # Redirect (POST 성공 시에도 1초 대기 랜딩 페이지 노출)
    params = {"code": code.code}
    if state:
        params["state"] = state
    
    target_url = f"{redirect_uri}?{urlencode(params)}"
    current_app.logger.info(f"Manual Login: Showing landing page for user {user.username}")
    
    return render_template(
        "sso_landing.html",
        target_url=target_url,
        username=user.username,
        app_title=current_app.config["APP_TITLE"]
    )


@auth_bp.route("/oauth/token", methods=["POST"])
def token():
    _, oauth_service = _get_services()

    current_app.logger.info(f"Token request from {request.remote_addr}: form={request.form}")

    grant_type = request.form.get("grant_type", "")
    client_id = request.form.get("client_id", "")
    client_secret = request.form.get("client_secret", "")

    # Authlib may send client credentials via Basic Auth Header
    if not client_id and request.authorization:
        client_id = request.authorization.username
        client_secret = request.authorization.password

    try:
        if grant_type == "authorization_code":
            code = request.form.get("code", "")
            redirect_uri = request.form.get("redirect_uri", "")
            token_obj = oauth_service.exchange_code_for_token(
                code_value=code,
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri=redirect_uri,
            )
        elif grant_type == "refresh_token":
            refresh_token = request.form.get("refresh_token", "")
            token_obj = oauth_service.refresh_access_token(
                refresh_token_value=refresh_token,
                client_id=client_id,
                client_secret=client_secret,
            )
        else:
            return {"error": f"unsupported_grant_type: {grant_type}"}, 400

        return token_obj.to_dict(), 200

    except ValueError as e:
        return {"error": str(e)}, 400


# ── Client CRUD UI ──

@auth_bp.route("/clients")
def client_list():
    """OAuth2 클라이언트 목록 조회 화면"""
    clients = OAuth2Client.query.order_by(OAuth2Client.id.desc()).all()
    return render_template(
        "client_list.html",
        clients=clients,
        app_title=current_app.config["APP_TITLE"]
    )


@auth_bp.route("/clients/add", methods=["GET", "POST"])
def client_add():
    """OAuth2 클라이언트 신규 등록 화면"""
    if request.method == "POST":
        try:
            client = OAuth2Client(
                client_id=request.form["client_id"],
                client_secret=request.form["client_secret"],
                client_name=request.form["client_name"],
                redirect_uris=request.form["redirect_uris"],
                grant_types=request.form.get("grant_types", "authorization_code refresh_token"),
                scope=request.form.get("scope", "openid profile email")
            )
            db.session.add(client)
            db.session.commit()
            flash(f"Client '{client.client_id}' registered successfully.", "success")
            return redirect(url_for("auth.client_list"))
        except Exception as e:
            flash(f"Error: {str(e)}", "danger")

    return render_template(
        "client_form.html",
        action="Add",
        app_title=current_app.config["APP_TITLE"]
    )


@auth_bp.route("/clients/edit/<int:id>", methods=["GET", "POST"])
def client_edit(id):
    """OAuth2 클라이언트 정보 수정 화면"""
    client = OAuth2Client.query.get_or_404(id)
    if request.method == "POST":
        try:
            client.client_id = request.form["client_id"]
            client.client_secret = request.form["client_secret"]
            client.client_name = request.form["client_name"]
            client.redirect_uris = request.form["redirect_uris"]
            client.grant_types = request.form.get("grant_types", "authorization_code refresh_token")
            client.scope = request.form.get("scope", "openid profile email")
            db.session.commit()
            flash(f"Client '{client.client_id}' updated successfully.", "success")
            return redirect(url_for("auth.client_list"))
        except Exception as e:
            flash(f"Error: {str(e)}", "danger")

    return render_template(
        "client_form.html",
        action="Edit",
        client=client,
        app_title=current_app.config["APP_TITLE"]
    )


@auth_bp.route("/clients/delete/<int:id>", methods=["POST"])
def client_delete(id):
    """OAuth2 클라이언트 삭제"""
    client = OAuth2Client.query.get_or_404(id)
    try:
        db.session.delete(client)
        db.session.commit()
        flash(f"Client '{client.client_id}' deleted successfully.", "success")
    except Exception as e:
        flash(f"Error deleting client: {str(e)}", "danger")
    return redirect(url_for("auth.client_list"))


@auth_bp.route("/logout")
def logout():
    logout_user()
    flash("Successfully logged out.", "success")
    return redirect(url_for("auth.index"))
