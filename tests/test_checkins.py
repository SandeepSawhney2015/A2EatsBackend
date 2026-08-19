from datetime import datetime, timezone

from app.core.redis import get_redis
from app.services import checkin_rules
from tests.conftest import checkin_payload


class TestCheckinValidation:
    def test_successful_checkin(self, client, auth_header, make_restaurant):
        r = client.post("/checkins", json=checkin_payload(make_restaurant()), headers=auth_header)
        assert r.status_code == 201
        body = r.json()
        assert body["points"] == 10
        assert body["restaurant_id"] == 1
        assert body["created_at"]  # time is stored

    def test_unknown_restaurant_is_404(self, client, auth_header):
        r = client.post(
            "/checkins",
            json={"restaurant_id": 999, "latitude": 42.0, "longitude": -83.0},
            headers=auth_header,
        )
        assert r.status_code == 404

    def test_requires_auth(self, client, make_restaurant):
        r = client.post("/checkins", json=checkin_payload(make_restaurant()))
        assert r.status_code in (401, 403)

    def test_too_far_from_restaurant_is_rejected(self, client, auth_header, make_restaurant):
        rest = make_restaurant()
        # ~0.7 miles north of the pin
        r = client.post(
            "/checkins",
            json=checkin_payload(rest, lat=rest["latitude"] + 0.01),
            headers=auth_header,
        )
        assert r.status_code == 400
        assert "Too far" in r.json()["detail"]

    def test_just_inside_200_feet_is_accepted(self, client, auth_header, make_restaurant):
        rest = make_restaurant()
        # ~180 ft north (1 degree latitude ~= 364,000 ft)
        r = client.post(
            "/checkins",
            json=checkin_payload(rest, lat=rest["latitude"] + 180 / 364_000),
            headers=auth_header,
        )
        assert r.status_code == 201


class TestCooldownAndLimits:
    def test_second_checkin_within_30_minutes_is_429(
        self, client, auth_header, make_restaurant
    ):
        first, second = make_restaurant(), make_restaurant(name="Other")
        client.post("/checkins", json=checkin_payload(first), headers=auth_header)
        r = client.post("/checkins", json=checkin_payload(second), headers=auth_header)
        assert r.status_code == 429

    def test_checkin_allowed_after_cooldown(
        self, client, auth_header, make_restaurant, skip_cooldown
    ):
        first, second = make_restaurant(), make_restaurant(name="Other")
        client.post("/checkins", json=checkin_payload(first), headers=auth_header)
        skip_cooldown()
        r = client.post("/checkins", json=checkin_payload(second), headers=auth_header)
        assert r.status_code == 201

    def test_same_restaurant_within_24h_is_409(
        self, client, auth_header, make_restaurant, skip_cooldown
    ):
        rest = make_restaurant()
        client.post("/checkins", json=checkin_payload(rest), headers=auth_header)
        skip_cooldown()
        r = client.post("/checkins", json=checkin_payload(rest), headers=auth_header)
        assert r.status_code == 409

    def test_daily_cap_of_10_is_enforced(self, client, auth_header, make_restaurant):
        rest = make_restaurant()
        day = datetime.now(timezone.utc).strftime("%Y%m%d")
        get_redis().set(f"daily_count:1:{day}", checkin_rules.MAX_CHECKINS_PER_DAY)
        r = client.post("/checkins", json=checkin_payload(rest), headers=auth_header)
        assert r.status_code == 429
        assert "Daily limit" in r.json()["detail"]

    def test_impossible_travel_is_rejected(
        self, client, auth_header, make_restaurant, skip_cooldown
    ):
        ann_arbor = make_restaurant()
        nyc = make_restaurant(name="Katz's", lat=40.7223, lng=-73.9874)
        client.post("/checkins", json=checkin_payload(ann_arbor), headers=auth_header)
        skip_cooldown()  # 31 min later, ~600 miles away -> not drivable
        r = client.post("/checkins", json=checkin_payload(nyc), headers=auth_header)
        assert r.status_code == 400

    def test_plausible_travel_is_accepted(
        self, client, auth_header, make_restaurant, skip_cooldown
    ):
        here = make_restaurant()
        nearby = make_restaurant(name="Nearby", lat=42.2803, lng=-83.7492)
        client.post("/checkins", json=checkin_payload(here), headers=auth_header)
        skip_cooldown()
        r = client.post("/checkins", json=checkin_payload(nearby), headers=auth_header)
        assert r.status_code == 201


class TestPoints:
    def test_first_ever_visit_earns_10(self, client, auth_header, make_restaurant):
        r = client.post("/checkins", json=checkin_payload(make_restaurant()), headers=auth_header)
        assert r.json()["points"] == 10

    def test_repeat_visit_earns_5_base(
        self, client, auth_header, make_restaurant, skip_cooldown
    ):
        rest = make_restaurant()
        client.post("/checkins", json=checkin_payload(rest), headers=auth_header)
        skip_cooldown()
        get_redis().delete("checkin_block:1:1")  # simulate the 24h block expiring
        # next day: reset the daily counter so the multiplier is 1x again
        day = datetime.now(timezone.utc).strftime("%Y%m%d")
        get_redis().delete(f"daily_count:1:{day}")
        r = client.post("/checkins", json=checkin_payload(rest), headers=auth_header)
        assert r.json()["points"] == 5

    def test_multiplier_reaches_5x_at_5th_checkin_and_caps(
        self, client, auth_header, make_restaurant, skip_cooldown
    ):
        earned = []
        for i in range(7):
            rest = make_restaurant(name=f"R{i}")
            if i > 0:
                skip_cooldown()
            r = client.post("/checkins", json=checkin_payload(rest), headers=auth_header)
            assert r.status_code == 201
            earned.append(r.json()["points"])
        assert earned == [10, 20, 30, 40, 50, 50, 50]


class TestMyCheckins:
    def test_lists_own_checkins_newest_first(
        self, client, auth_header, make_restaurant, skip_cooldown
    ):
        a, b = make_restaurant(name="A"), make_restaurant(name="B")
        client.post("/checkins", json=checkin_payload(a), headers=auth_header)
        skip_cooldown()
        client.post("/checkins", json=checkin_payload(b), headers=auth_header)
        rows = client.get("/checkins/me", headers=auth_header).json()
        assert [c["restaurant_id"] for c in rows] == [b["id"], a["id"]]
