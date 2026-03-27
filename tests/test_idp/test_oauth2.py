"""OAuth2 Flow 통합 테스트. Coverage 목표: routes.py, oauth_service.py 100%"""
from urllib.parse import urlparse, parse_qs


class TestAuthorize:
    def test_authorize_get_shows_login(self, client, db, sample_oauth_client):
        resp = client.get("/oauth/authorize", query_string={
            "client_id": "test-client",
            "redirect_uri": "http://localhost/callback",
            "response_type": "code",
        })
        assert resp.status_code == 200
        assert b"username" in resp.data

    def test_authorize_invalid_client(self, client, db):
        resp = client.get("/oauth/authorize", query_string={
            "client_id": "nonexistent",
            "redirect_uri": "http://localhost/callback",
            "response_type": "code",
        })
        assert resp.status_code == 400

    def test_authorize_invalid_redirect_uri(self, client, db, sample_oauth_client):
        resp = client.get("/oauth/authorize", query_string={
            "client_id": "test-client",
            "redirect_uri": "http://evil.com/callback",
            "response_type": "code",
        })
        assert resp.status_code == 400

    def test_authorize_invalid_response_type(self, client, db, sample_oauth_client):
        resp = client.get("/oauth/authorize", query_string={
            "client_id": "test-client",
            "redirect_uri": "http://localhost/callback",
            "response_type": "token",
        })
        assert resp.status_code == 400

    def test_authorize_post_success(self, client, db, sample_user, sample_oauth_client):
        resp = client.post(
            "/oauth/authorize?client_id=test-client"
            "&redirect_uri=http://localhost/callback"
            "&response_type=code&scope=openid+profile+email",
            data={"username": "testuser", "password": "TestPass123!"},
        )
        assert resp.status_code == 302
        location = resp.headers["Location"]
        assert "code=" in location
        parsed = urlparse(location)
        assert parsed.hostname == "localhost"

    def test_authorize_post_with_state(self, client, db, sample_user,
                                       sample_oauth_client):
        resp = client.post(
            "/oauth/authorize?client_id=test-client"
            "&redirect_uri=http://localhost/callback"
            "&response_type=code&state=xyz123",
            data={"username": "testuser", "password": "TestPass123!"},
        )
        assert resp.status_code == 302
        assert "state=xyz123" in resp.headers["Location"]

    def test_authorize_post_bad_credentials(self, client, db, sample_user,
                                             sample_oauth_client):
        resp = client.post(
            "/oauth/authorize?client_id=test-client"
            "&redirect_uri=http://localhost/callback"
            "&response_type=code",
            data={"username": "testuser", "password": "wrong"},
        )
        assert resp.status_code == 401


class TestTokenExchange:
    def _get_code(self, client, sample_user, sample_oauth_client):
        resp = client.post(
            "/oauth/authorize?client_id=test-client"
            "&redirect_uri=http://localhost/callback"
            "&response_type=code",
            data={"username": "testuser", "password": "TestPass123!"},
        )
        location = resp.headers["Location"]
        qs = parse_qs(urlparse(location).query)
        return qs["code"][0]

    def test_token_exchange_success(self, client, db, sample_user,
                                     sample_oauth_client):
        code = self._get_code(client, sample_user, sample_oauth_client)
        resp = client.post("/oauth/token", data={
            "grant_type": "authorization_code",
            "code": code,
            "client_id": "test-client",
            "client_secret": "test-secret",
            "redirect_uri": "http://localhost/callback",
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "Bearer"

    def test_token_invalid_code(self, client, db, sample_oauth_client):
        resp = client.post("/oauth/token", data={
            "grant_type": "authorization_code",
            "code": "invalid_code",
            "client_id": "test-client",
            "client_secret": "test-secret",
            "redirect_uri": "http://localhost/callback",
        })
        assert resp.status_code == 400

    def test_token_invalid_client_secret(self, client, db, sample_user,
                                          sample_oauth_client):
        code = self._get_code(client, sample_user, sample_oauth_client)
        resp = client.post("/oauth/token", data={
            "grant_type": "authorization_code",
            "code": code,
            "client_id": "test-client",
            "client_secret": "wrong-secret",
            "redirect_uri": "http://localhost/callback",
        })
        assert resp.status_code == 400

    def test_unsupported_grant_type(self, client, db):
        resp = client.post("/oauth/token", data={
            "grant_type": "implicit",
            "client_id": "test-client",
            "client_secret": "test-secret",
        })
        assert resp.status_code == 400


class TestRefreshToken:
    def _get_tokens(self, client, sample_user, sample_oauth_client):
        # 전체 flow: authorize → token
        resp = client.post(
            "/oauth/authorize?client_id=test-client"
            "&redirect_uri=http://localhost/callback"
            "&response_type=code",
            data={"username": "testuser", "password": "TestPass123!"},
        )
        qs = parse_qs(urlparse(resp.headers["Location"]).query)
        code = qs["code"][0]

        resp2 = client.post("/oauth/token", data={
            "grant_type": "authorization_code",
            "code": code,
            "client_id": "test-client",
            "client_secret": "test-secret",
            "redirect_uri": "http://localhost/callback",
        })
        return resp2.get_json()

    def test_refresh_token_success(self, client, db, sample_user,
                                    sample_oauth_client):
        tokens = self._get_tokens(client, sample_user, sample_oauth_client)
        resp = client.post("/oauth/token", data={
            "grant_type": "refresh_token",
            "refresh_token": tokens["refresh_token"],
            "client_id": "test-client",
            "client_secret": "test-secret",
        })
        assert resp.status_code == 200
        new_tokens = resp.get_json()
        assert new_tokens["access_token"] != tokens["access_token"]

    def test_refresh_token_invalid(self, client, db, sample_oauth_client):
        resp = client.post("/oauth/token", data={
            "grant_type": "refresh_token",
            "refresh_token": "invalid_refresh",
            "client_id": "test-client",
            "client_secret": "test-secret",
        })
        assert resp.status_code == 400


class TestIndexPage:
    def test_index(self, client, db):
        resp = client.get("/")
        assert resp.status_code == 200
