from tests.conftest import offers_stream


async def test_create_campaign_builds_two_streams(client, keitaro, campaign):
    assert campaign["name"] == "campaign 2"
    assert campaign["geo"] == ["AU"]
    assert campaign["url"] == f"https://kylovoa.com/{campaign['alias']}"
    assert [s["position"] for s in campaign["streams"]] == [1, 2]

    # Keitaro received the right payloads
    created_campaign = next(p for name, p in keitaro.calls if name == "create_campaign")
    assert created_campaign["domain_id"] == 1813  # kylovoa.com
    assert created_campaign["group_id"] == 10332  # FORTESTS
    assert created_campaign["traffic_source_id"] == 836  # FORTESTS
    assert created_campaign["type"] == "position"

    geo, offers = [p for name, p in keitaro.calls if name == "create_stream"]
    assert geo["schema"] == "redirect" and geo["action_payload"] == "https://google.com"
    assert geo["filters"] == [{"name": "country", "mode": "accept", "payload": ["AU"]}]
    assert geo["position"] < offers["position"]
    assert offers["schema"] == "landings"
    assert offers["offers"] == [{"offer_id": 3749, "share": 100, "state": "active"}]

    stream = offers_stream(campaign)
    assert stream["offers"][0]["share"] == 100 and stream["is_dirty"] is False


async def test_geo_string_is_normalised(client):
    r = await client.post("/api/v1/campaigns", json={"name": "x", "geo": "mx, au RO,mx", "offer_id": 3717})
    assert r.status_code == 201
    assert r.json()["geo"] == ["MX", "AU", "RO"]


async def test_invalid_geo_rejected(client):
    r = await client.post("/api/v1/campaigns", json={"name": "x", "geo": "Australia", "offer_id": 3717})
    assert r.status_code == 422


async def test_unknown_offer_returns_404(client, keitaro):
    r = await client.post("/api/v1/campaigns", json={"name": "x", "geo": "AU", "offer_id": 999999})
    assert r.status_code == 404
    assert not keitaro.campaigns  # nothing created in Keitaro


async def test_stream_failure_rolls_back_campaign(client, keitaro):
    keitaro.fail_on = "create_stream"
    r = await client.post("/api/v1/campaigns", json={"name": "x", "geo": "AU", "offer_id": 3749})
    assert r.status_code == 502
    assert all(c["state"] == "deleted" for c in keitaro.campaigns.values())
    assert (await client.get("/api/v1/campaigns")).json() == []
