class TestSignupUsername:
    def test_first_signup_without_username_is_422(self, client, apple_stub):
        r = client.post("/auth/apple", json={"identity_token": "stub"})
        assert r.status_code == 422
        assert r.json()["detail"] == "username_required"

    def test_signup_with_username_works(self, client, apple_stub, auth_header):
        me = client.get("/users/me", headers=auth_header).json()
        assert me["username"] == "testuser"

    def test_returning_user_does_not_need_username(self, client, apple_stub, auth_header):
        r = client.post("/auth/apple", json={"identity_token": "stub"})
        assert r.status_code == 200

    def test_duplicate_username_is_409(self, auth_header, sign_up):
        r = sign_up("other.apple.sub", "testuser")
        assert r.status_code == 409
        assert "taken" in r.json()["detail"]

    def test_username_uniqueness_is_case_insensitive(self, auth_header, sign_up):
        r = sign_up("other.apple.sub", "TestUser")
        assert r.status_code == 409

    def test_username_is_stored_lowercase(self, client, sign_up):
        r = sign_up("other.apple.sub", "CoolEater99")
        access = r.json()["access_token"]
        me = client.get("/users/me", headers={"Authorization": f"Bearer {access}"}).json()
        assert me["username"] == "cooleater99"

    def test_invalid_username_format_rejected(self, client, apple_stub):
        for bad in ["ab", "way_too_long_username_over_20", "has space", "has-dash", "emoji😀"]:
            r = client.post("/auth/apple", json={"identity_token": "stub", "username": bad})
            assert r.status_code == 422, bad


class TestUsernameChange:
    def test_change_username(self, client, auth_header):
        r = client.patch("/users/me/username", json={"username": "newname"}, headers=auth_header)
        assert r.status_code == 200
        assert r.json()["username"] == "newname"

    def test_change_to_taken_name_is_409(self, client, auth_header, sign_up):
        sign_up("other.apple.sub", "occupied")
        r = client.patch("/users/me/username", json={"username": "occupied"}, headers=auth_header)
        assert r.status_code == 409

    def test_third_change_in_a_month_is_429(self, client, auth_header):
        assert client.patch("/users/me/username", json={"username": "first"}, headers=auth_header).status_code == 200
        assert client.patch("/users/me/username", json={"username": "second"}, headers=auth_header).status_code == 200
        r = client.patch("/users/me/username", json={"username": "third"}, headers=auth_header)
        assert r.status_code == 429
        # and the name is unchanged
        assert client.get("/users/me", headers=auth_header).json()["username"] == "second"

    def test_noop_change_does_not_burn_a_change(self, client, auth_header):
        client.patch("/users/me/username", json={"username": "keeper"}, headers=auth_header)
        # "changing" to the same name repeatedly costs nothing
        client.patch("/users/me/username", json={"username": "keeper"}, headers=auth_header)
        client.patch("/users/me/username", json={"username": "keeper"}, headers=auth_header)
        r = client.patch("/users/me/username", json={"username": "onemore"}, headers=auth_header)
        assert r.status_code == 200

    def test_requires_auth(self, client):
        r = client.patch("/users/me/username", json={"username": "sneaky"})
        assert r.status_code in (401, 403)


class TestLeaderboardShowsUsername:
    def test_leaderboard_uses_username(self, client, auth_header, make_restaurant):
        from tests.conftest import checkin_payload

        client.post("/checkins", json=checkin_payload(make_restaurant()), headers=auth_header)
        board = client.get("/leaderboard/users").json()
        assert board[0]["username"] == "testuser"
