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


def test_default_is_matched_by_name_only():
    from app.services.keitaro_meta import _find_id

    assert _find_id([{"id": 1813, "name": "kylovoa.com"}], "https://kylovoa.com/", domain=True) == 1813
    assert _find_id([{"id": 836, "name": "FORTESTS"}], " fortests ") == 836
    # a single other item is NOT picked silently
    assert _find_id([{"id": 1813, "name": "kylovoa.com"}], "in.posdk.xyz", domain=True) is None
    assert _find_id([{"id": 1, "name": "a"}, {"id": 2, "name": "b"}], "c") is None


async def test_archived_default_source_gives_clear_error(client, keitaro):
    # FORTESTS archived in Keitaro → it is no longer in GET /traffic_sources
    keitaro.sources = [{"id": 900, "name": "Other source"}]
    assert (await client.get("/api/v1/meta")).json()["default_traffic_source_id"] is None

    body = {"name": "c", "geo": "AU", "offer_id": 3749}
    r = await client.post("/api/v1/campaigns", json=body)
    assert r.status_code == 422
    detail = r.json()["detail"]
    assert '"FORTESTS" (DEFAULT_TRAFFIC_SOURCE)' in detail
    assert "1 active traffic sources" in detail
    assert not keitaro.campaigns  # nothing was created in Keitaro

    # picking a source explicitly still works
    r = await client.post("/api/v1/campaigns", json={**body, "traffic_source_id": 900})
    assert r.status_code == 201, r.text
