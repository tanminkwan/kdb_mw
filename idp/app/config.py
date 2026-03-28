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
    # For RS256 signing, providing a fixed development key if not set.
    # IN PRODUCTION: Set IDP_RSA_PRIVATE_KEY environment variable.
    IDP_RSA_PRIVATE_KEY = os.getenv("IDP_RSA_PRIVATE_KEY", (
        "-----BEGIN PRIVATE KEY-----\n"
        "MIIEugIBADANBgkqhkiG9w0BAQEFAASCBKQwggSgAgEAAoIBAQC8leDKAXXLSXMg\n"
        "5+w/chxXcVqxQHhWQsyOcUGovVcdi5Qgh+cHqAtOgwE/UlfnOI/6nUfnahYHIPVI\n"
        "eOCiSzQiFJe2TKqs4eHEduaSKa1wrqlrzBNv282UHin9xQ280x2kztzMHuZYoUSu\n"
        "KmVUMCZ2OXbDEctNSexNcYVF62PlcJfJ65TDuXry4V0YPcrxELCBhCURc9RUfrQX\n"
        "v9sWK7n0I0dgbGa5/IfY0MUNjE+5zCgMtwjiC9rDyDfhfqdwtWgCLHkfZzTtXW6E\n"
        "c51L45KbPaxoM/ujQ7+jiS+PlDm48RQgeVDJNNX0uQEH3/ewlTS73wpqH+L60lUF\n"
        "ruM/46D7AgMBAAECgf8Ynoy4AzO06palNRekffX8V/ahktM3OtqiL6jy9tEZZb/q\n"
        "p+ur6YtXcYXexHmUzFGeBpURUbXbrjrxsv682+O7k1IafH4c2tYaZC5kYF3ILXbo\n"
        "kZUs1nr17YRU+D4V7J5FZbgD0WJVP/2EjnINjZkebF3+Yn75QLNl4rc4Lp0fB3Dg\n"
        "wfX+DWvl81o9ffUh0t/ltvCo64TSzJHBeNHU32gNrjbBlGQoU/J7kVHv5/0egDrm\n"
        "IYFfa9DNfknRTwPPZQwX6pf9xVbI+Ted/txz+ymfztn2qFm3E68EbtZyPSWUnARs\n"
        "qNUoIiRTpzmqP1JScCfi4nGPkYs5ZS9SHKP4LCkCgYEA25OGm7t/fSOOX1z3Q0NJ\n"
        "BwQnaAxrhab2nAjso54KbnPSNi+huH5kHIzDHDiNjzoNi4rLVIipalfrbaSGbP0N\n"
        "kpbBDCy39qfDy/U67NFUndqvJ1KZfFDP8imo0pf+dRjiIHvwHOoFILKd0LlXpGP0\n"
        "ualTO27nB2GdBleyP7w6HEkCgYEA295NxKiOumdA5kNOQXwGOj9HICmL9DzRQlCH\n"
        "rl27SOfpIUyiw/Fj8VZ08CqfJRmR3hSGThE9INSdDMvCXzvPeBJFhCYPBAeB6HIc\n"
        "4//ezbTOPC43XtxHptHNSmC31DwJR0cUhD/dWwrlDI3oDkEITYvSx9yM3NJF7o1w\n"
        "YbilqyMCgYBRR/cYRvwWksbtPji5yXqLAlqkBZT30KqRcCxJFQO/h1hVfqRa606b\n"
        "0u+Wzsh4MIE7GpHSJRSxrQIVgEXSqooPrYagvx0KTWgJZCn/6C1ukbks0ULH5hJU\n"
        "Dl/UNTeYmTF73OUxjt9/Dx+kWDe9PtMkty18Xr1e2h+KbYQqW78XIQKBgFlY1TF9\n"
        "bcLCAtWPtFVYGQ/CdxzSxVTTAhZ4sypgXKMb2tj1U49coMiJ4atXJqTk5yngHVPM\n"
        "HZMh01BH3QzmOUEJ68Xv0VpJ0riq5qKgb+IX/1blUQrzaQqZZ1s6Qnm0i/CzKds0\n"
        "OLeujbW0VQC13LHmiBk/vt5ddJ2kTG7poikRAoGAVqU5Lw6x63/3aTjbEnyJXC91\n"
        "UEm3N3PU8f6mTq8nopxRH1FrfIB1vH7xgnV8HnHi6e7FkGXc7XimgaUDFPzBkQ7/\n"
        "5ig/aFwt4bllqXz1x8dXM6/fBd4QyqU51UdDccHgsSmp++8+sg2KOwBVd6DRIthA\n"
        "sC+cmgOcCELofm4I6X8=\n"
        "-----END PRIVATE KEY-----"
    ))

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
