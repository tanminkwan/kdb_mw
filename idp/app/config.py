import os


class Config:
    """IDP 서버 기본 설정. 모든 설정값은 환경변수 우선, 기본값 보조."""

    # ── DB ──
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "IDP_DATABASE_URI",
        "postgresql://tiffanie:1q2w3e4r!!@localhost:5433/idp"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_COOKIE_NAME = "mwm_idp_session"

    # ── Security ──
    SECRET_KEY = os.getenv("IDP_SECRET_KEY", "dev-only-secret-change-me")
    PREFERRED_URL_SCHEME = 'https'
    PASSWORD_HASH_METHOD = "bcrypt"
    PASSWORD_MIN_LENGTH = int(os.getenv("IDP_PASSWORD_MIN_LENGTH", "8"))

    # ── OAuth2 ──
    OAUTH2_TOKEN_EXPIRES_IN = int(os.getenv("OAUTH2_TOKEN_EXPIRES_IN", "3600"))
    OAUTH2_REFRESH_TOKEN_EXPIRES_IN = int(
        os.getenv("OAUTH2_REFRESH_TOKEN_EXPIRES_IN", "86400")
    )

    # ── Default Client (mwm-app) ──
    DEFAULT_CLIENT_ID = os.getenv("IDP_MWM_CLIENT_ID", "mwm-client")
    DEFAULT_CLIENT_SECRET = os.getenv("IDP_MWM_CLIENT_SECRET", "mwm-secret")
    DEFAULT_REDIRECT_URI = os.getenv(
        "IDP_MWM_REDIRECT_URI",
        "http://localhost:8000/idp/callback"
    )

    # ── UI ──
    APP_TITLE = os.getenv("IDP_APP_TITLE", "MWM Identity Provider")

    # ── OIDC (OpenID Connect) ──
    OIDC_ISSUER = os.getenv("OIDC_ISSUER", "http://localhost:5000")
    # RS256 signing key.
    # IN PRODUCTION: IDP_RSA_PRIVATE_KEY specifies the path to the PEM file.
    IDP_RSA_PRIVATE_KEY = os.getenv("IDP_RSA_PRIVATE_KEY", "/etc/idp/certs/idp_private.pem")


    # ── Logging ──
    LOG_LEVEL = os.getenv("IDP_LOG_LEVEL", "INFO")

    # ── Sync ──
    SYNC_SOURCES = {
        "mwm_app": {
            "description": "리발소(mwm-app) 사용자",
            "db_uri": os.getenv(
                "SYNC_MWM_DB_URI",
                "postgresql://tiffanie:1q2w3e4r!!@mwm-db:5432/mw"
            ),
            "table": "ab_user",
            "id_column": "id",
            "column_mapping": {
                "username": "username",
                "email": "email",
                "first_name": "first_name",
                "last_name": "last_name",
                "password_hash": "password",
                "active": "active",
            },
            "role_source": {
                "type": "join",
                "join_table": "ab_user_role",
                "join_user_column": "user_id",
                "join_role_column": "role_id",
                "role_table": "ab_role",
                "role_id_column": "id",
                "role_name_column": "name",
            },
            "filter": "active = true",
            "sync_password": True,
            "auto_sync_interval_minutes": 0,
        }
    }


class TestConfig(Config):
    """테스트 전용 설정"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    SECRET_KEY = "test-secret-key"
    SYNC_SOURCES = {}
