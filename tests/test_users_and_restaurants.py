from tests.conftest import checkin_payload


class TestUserStats:
    def test_new_user_has_empty_stats(self, client, auth_header):
        me = client.get("/users/me", headers=auth_header).json()
        assert me["points"] == 0
        assert me["top_restaurant_id"] is None
        assert me["flavor_profile"] == []

    def test_points_are_summed_from_checkins(
        self, client, auth_header, make_restaurant, skip_cooldown
    ):
        a, b = make_restaurant(name="A"), make_restaurant(name="B")
        client.post("/checkins", json=checkin_payload(a), headers=auth_header)  # 10
        skip_cooldown()
        client.post("/checkins", json=checkin_payload(b), headers=auth_header)  # 20 (2x)
        me = client.get("/users/me", headers=auth_header).json()
        assert me["points"] == 30

    def test_top_restaurant_is_most_visited(
        self, client, auth_header, make_restaurant, skip_cooldown
    ):
        from app.core.redis import get_redis

        a, b = make_restaurant(name="A"), make_restaurant(name="B")
        client.post("/checkins", json=checkin_payload(a), headers=auth_header)
        skip_cooldown()
        client.post("/checkins", json=checkin_payload(b), headers=auth_header)
        skip_cooldown()
        get_redis().delete(f"checkin_block:1:{b['id']}")  # 24h passed for B
        client.post("/checkins", json=checkin_payload(b), headers=auth_header)
        me = client.get("/users/me", headers=auth_header).json()
        assert me["top_restaurant_id"] == b["id"]

    def test_flavor_profile_lists_distinct_restaurants(
        self, client, auth_header, make_restaurant, skip_cooldown
    ):
        a, b = make_restaurant(name="A"), make_restaurant(name="B")
        client.post("/checkins", json=checkin_payload(a), headers=auth_header)
        skip_cooldown()
        client.post("/checkins", json=checkin_payload(b), headers=auth_header)
        me = client.get("/users/me", headers=auth_header).json()
        assert sorted(me["flavor_profile"]) == [a["id"], b["id"]]


class TestRestaurants:
    def test_create_and_list(self, client, make_restaurant):
        make_restaurant(name="One")
        make_restaurant(name="Two")
        rows = client.get("/restaurants").json()
        assert [r["name"] for r in rows] == ["One", "Two"]

    def test_detail_includes_summed_points(
        self, client, auth_header, make_restaurant
    ):
        rest = make_restaurant()
        client.post("/checkins", json=checkin_payload(rest), headers=auth_header)
        detail = client.get(f"/restaurants/{rest['id']}").json()
        assert detail["points"] == 10
        assert detail["latitude"] == rest["latitude"]

    def test_unknown_restaurant_detail_is_404(self, client):
        assert client.get("/restaurants/999").status_code == 404

    def test_create_without_admin_token_is_rejected(self, client):
        body = {"name": "Sneaky", "address": "x", "latitude": 0.0, "longitude": 0.0}
        assert client.post("/restaurants", json=body).status_code == 422  # header missing
        r = client.post("/restaurants", json=body, headers={"X-Admin-Token": "wrong"})
        assert r.status_code == 401


class TestHealth:
    def test_health(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}
