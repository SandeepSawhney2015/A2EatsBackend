from unittest.mock import patch

import jwt as pyjwt


class TestAppleSignIn:
    def test_returns_access_and_refresh_tokens(self, client, apple_stub):
        r = client.post("/auth/apple", json={"identity_token": "stub"})
        assert r.status_code == 200
        body = r.json()
        assert body["access_token"]
        assert body["refresh_token"]
        assert body["token_type"] == "bearer"

    def test_invalid_apple_token_is_401(self, client):
        with patch(
            "app.routers.apple_auth.verify_apple_token",
            side_effect=pyjwt.InvalidTokenError,
        ):
            r = client.post("/auth/apple", json={"identity_token": "garbage"})
        assert r.status_code == 401

    def test_expired_apple_token_is_401(self, client):
        with patch(
            "app.routers.apple_auth.verify_apple_token",
            side_effect=pyjwt.ExpiredSignatureError,
        ):
            r = client.post("/auth/apple", json={"identity_token": "old"})
        assert r.status_code == 401

    def test_signing_in_twice_reuses_the_same_user(self, client, apple_stub):
        h1 = {"Authorization": f"Bearer {client.post('/auth/apple', json={'identity_token': 's'}).json()['access_token']}"}
        h2 = {"Authorization": f"Bearer {client.post('/auth/apple', json={'identity_token': 's'}).json()['access_token']}"}
        assert client.get("/users/me", headers=h1).json()["id"] == client.get("/users/me", headers=h2).json()["id"]

    def test_email_saved_on_first_sign_in(self, client, apple_stub, auth_header):
        me = client.get("/users/me", headers=auth_header).json()
        assert me["email"] == "test@example.com"


class TestRefresh:
    def test_refresh_returns_new_pair(self, client, apple_stub):
        tokens = client.post("/auth/apple", json={"identity_token": "s"}).json()
        r = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
        assert r.status_code == 200
        assert r.json()["access_token"]
        assert r.json()["refresh_token"] != tokens["refresh_token"]

    def test_old_refresh_token_dies_after_rotation(self, client, apple_stub):
        tokens = client.post("/auth/apple", json={"identity_token": "s"}).json()
        client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
        r = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
        assert r.status_code == 401

    def test_unknown_refresh_token_is_401(self, client):
        r = client.post("/auth/refresh", json={"refresh_token": "never-issued"})
        assert r.status_code == 401

    def test_refreshed_access_token_works(self, client, apple_stub):
        tokens = client.post("/auth/apple", json={"identity_token": "s"}).json()
        new = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]}).json()
        r = client.get("/users/me", headers={"Authorization": f"Bearer {new['access_token']}"})
        assert r.status_code == 200


class TestLogout:
    def test_logout_revokes_the_session(self, client, apple_stub):
        tokens = client.post("/auth/apple", json={"identity_token": "s"}).json()
        r = client.post("/auth/logout", json={"refresh_token": tokens["refresh_token"]})
        assert r.status_code == 204
        r = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
        assert r.status_code == 401


class TestProtectedRoutes:
    def test_no_token_is_rejected(self, client):
        assert client.get("/users/me").status_code in (401, 403)

    def test_garbage_token_is_rejected(self, client):
        r = client.get("/users/me", headers={"Authorization": "Bearer not-a-jwt"})
        assert r.status_code == 401

    def test_token_signed_with_wrong_secret_is_rejected(self, client):
        forged = pyjwt.encode({"sub": "1"}, "wrong-secret", algorithm="HS256")
        r = client.get("/users/me", headers={"Authorization": f"Bearer {forged}"})
        assert r.status_code == 401
