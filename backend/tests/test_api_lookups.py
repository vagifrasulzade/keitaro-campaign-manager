async def test_meta_defaults_resolved_by_name(client):
    r = await client.get("/api/v1/meta")
    data = r.json()
    assert data["default_domain_id"] == 1813
    assert data["default_group_id"] == 10332
    assert data["default_traffic_source_id"] == 836


async def test_offer_autocomplete(client):
    by_name = (await client.get("/api/v1/offers", params={"q": "miaflow"})).json()
    assert {o["id"] for o in by_name} == {3749, 3717}
    by_id = (await client.get("/api/v1/offers", params={"q": "374"})).json()
    assert [o["id"] for o in by_id] == [3749]


async def test_health(client):
    assert (await client.get("/health")).json() == {"status": "ok"}


def test_single_item_is_used_when_default_name_is_missing():
    from app.services.keitaro_meta import _find_id

    assert _find_id([{"id": 1813, "name": "kylovoa.com"}], "in.posdk.xyz", domain=True) == 1813
    assert _find_id([{"id": 1, "name": "a"}, {"id": 2, "name": "b"}], "c") is None
    assert _find_id([{"id": 1813, "name": "kylovoa.com"}], "https://kylovoa.com/", domain=True) == 1813
