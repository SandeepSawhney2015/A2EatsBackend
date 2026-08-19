from app.core.redis import get_redis
from tests.conftest import checkin_payload


class TestUserLeaderboard:
    def test_empty_when_no_checkins(self, client):
        assert client.get("/leaderboard/users").json() == []

    def test_ranked_by_points(self, client, auth_header, make_restaurant, skip_cooldown):
        a, b = make_restaurant(name="A"), make_restaurant(name="B")
        client.post("/checkins", json=checkin_payload(a), headers=auth_header)
        skip_cooldown()
        client.post("/checkins", json=checkin_payload(b), headers=auth_header)
        board = client.get("/leaderboard/users").json()
        assert len(board) == 1
        assert board[0]["rank"] == 1
        assert board[0]["points"] == 30

    def test_fewer_than_20_users_returns_them_all(self, client, auth_header, make_restaurant):
        client.post("/checkins", json=checkin_payload(make_restaurant()), headers=auth_header)
        board = client.get("/leaderboard/users").json()
        assert len(board) == 1  # just the users that exist

    def test_cached_until_ttl_expires(self, client, auth_header, make_restaurant, skip_cooldown):
        a, b = make_restaurant(name="A"), make_restaurant(name="B")
        client.post("/checkins", json=checkin_payload(a), headers=auth_header)

        # first request computes and caches (10 points)
        first = client.get("/leaderboard/users").json()
        assert first[0]["points"] == 10

        # new checkin happens, but the cached board is still served
        skip_cooldown()
        client.post("/checkins", json=checkin_payload(b), headers=auth_header)
        cached = client.get("/leaderboard/users").json()
        assert cached[0]["points"] == 10

        # cache dies -> next request recomputes
        get_redis().delete("leaderboard:users")
        fresh = client.get("/leaderboard/users").json()
        assert fresh[0]["points"] == 30

    def test_cache_key_has_24h_ttl(self, client, auth_header, make_restaurant):
        client.post("/checkins", json=checkin_payload(make_restaurant()), headers=auth_header)
        client.get("/leaderboard/users")
        ttl = get_redis().ttl("leaderboard:users")
        assert 0 < ttl <= 24 * 60 * 60


class TestRestaurantLeaderboard:
    def test_ranked_by_summed_points(self, client, auth_header, make_restaurant, skip_cooldown):
        a, b = make_restaurant(name="A"), make_restaurant(name="B")
        client.post("/checkins", json=checkin_payload(a), headers=auth_header)  # 10 pts
        skip_cooldown()
        client.post("/checkins", json=checkin_payload(b), headers=auth_header)  # 20 pts (2x)
        board = client.get("/leaderboard/restaurants").json()
        assert [e["name"] for e in board] == ["B", "A"]
        assert [e["points"] for e in board] == [20, 10]
        assert [e["rank"] for e in board] == [1, 2]

    def test_restaurant_with_no_checkins_not_listed(self, client, auth_header, make_restaurant):
        a = make_restaurant(name="A")
        make_restaurant(name="Never Visited")
        client.post("/checkins", json=checkin_payload(a), headers=auth_header)
        board = client.get("/leaderboard/restaurants").json()
        assert [e["name"] for e in board] == ["A"]
