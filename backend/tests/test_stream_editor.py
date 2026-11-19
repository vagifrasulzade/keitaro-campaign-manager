from tests.conftest import offers_stream, shares


async def _stream(campaign):
    return offers_stream(campaign)["id"]


async def test_add_offers_rebalances(client, campaign):
    sid = await _stream(campaign)
    r = await client.post(f"/api/v1/streams/{sid}/offers", json={"offer_id": 3717})
    assert shares(r.json()) == {3749: 50, 3717: 50}
    r = await client.post(f"/api/v1/streams/{sid}/offers", json={"offer_id": 3801})
    body = r.json()
    assert shares(body) == {3749: 34, 3717: 33, 3801: 33}
    assert body["total_share"] == 100 and body["is_dirty"] is True


async def test_duplicate_offer_conflict(client, campaign):
    sid = await _stream(campaign)
    r = await client.post(f"/api/v1/streams/{sid}/offers", json={"offer_id": 3749})
    assert r.status_code == 409


async def test_pin_and_unpin(client, campaign):
    sid = await _stream(campaign)
    for oid in (3717, 3801):
        await client.post(f"/api/v1/streams/{sid}/offers", json={"offer_id": oid})
    r = await client.patch(f"/api/v1/streams/{sid}/offers/3749", json={"share": 60})
    assert shares(r.json()) == {3749: 60, 3717: 20, 3801: 20}
    # pin that leaves no room for others → 422, state unchanged
    r = await client.patch(f"/api/v1/streams/{sid}/offers/3717", json={"share": 40})
    assert r.status_code == 422
    r = await client.get(f"/api/v1/streams/{sid}")
    assert shares(r.json()) == {3749: 60, 3717: 20, 3801: 20}
    r = await client.patch(f"/api/v1/streams/{sid}/offers/3749", json={"share": None})
    assert shares(r.json()) == {3749: 34, 3717: 33, 3801: 33}


async def test_remove_restore_push_cancel(client, keitaro, campaign):
    sid = await _stream(campaign)
    await client.post(f"/api/v1/streams/{sid}/offers", json={"offer_id": 3717})
    r = await client.post(f"/api/v1/streams/{sid}/push")
    assert r.json()["is_dirty"] is False
    assert keitaro.streams[sid]["offers"][0]["share"] == 50

    # remove published offer → archived as removed, other gets 100
    r = await client.delete(f"/api/v1/streams/{sid}/offers/3749")
    body = r.json()
    assert shares(body) == {3717: 100}
    removed = next(o for o in body["offers"] if o["offer_id"] == 3749)
    assert removed["status"] == "removed" and removed["share"] == 0

    # bring back
    r = await client.post(f"/api/v1/streams/{sid}/offers/3749/restore")
    assert shares(r.json()) == {3749: 50, 3717: 50}
    assert r.json()["is_dirty"] is False  # same as published

    # remove + add new, then cancel → back to published 50/50
    await client.delete(f"/api/v1/streams/{sid}/offers/3749")
    await client.post(f"/api/v1/streams/{sid}/offers", json={"offer_id": 3801})
    r = await client.post(f"/api/v1/streams/{sid}/cancel")
    body = r.json()
    assert shares(body) == {3749: 50, 3717: 50}
    assert all(o["offer_id"] != 3801 for o in body["offers"])
    assert body["is_dirty"] is False


async def test_push_sends_only_active_offers(client, keitaro, campaign):
    sid = await _stream(campaign)
    await client.post(f"/api/v1/streams/{sid}/offers", json={"offer_id": 3717})
    await client.post(f"/api/v1/streams/{sid}/push")
    await client.delete(f"/api/v1/streams/{sid}/offers/3717")
    await client.post(f"/api/v1/streams/{sid}/push")
    last_put = [p for name, p in keitaro.calls if name == "update_stream"][-1]
    assert last_put == {"offers": [{"offer_id": 3749, "share": 100, "state": "active"}]}


async def test_push_without_active_offers_fails(client, campaign):
    sid = await _stream(campaign)
    await client.delete(f"/api/v1/streams/{sid}/offers/3749")
    r = await client.post(f"/api/v1/streams/{sid}/push")
    assert r.status_code == 422


async def test_remove_releases_pins_when_rest_cannot_sum_to_100(client, campaign):
    sid = await _stream(campaign)
    for oid in (3717, 3801):
        await client.post(f"/api/v1/streams/{sid}/offers", json={"offer_id": oid})
    await client.patch(f"/api/v1/streams/{sid}/offers/3749", json={"share": 50})
    await client.patch(f"/api/v1/streams/{sid}/offers/3717", json={"share": 30})
    r = await client.delete(f"/api/v1/streams/{sid}/offers/3801")  # 3801 was a draft → deleted
    body = r.json()
    assert shares(body) == {3749: 50, 3717: 50}
    assert not any(o["is_pinned"] for o in body["offers"])


async def test_redirect_stream_is_not_editable(client, campaign):
    geo_id = next(s["id"] for s in campaign["streams"] if s["schema"] == "redirect")
    r = await client.post(f"/api/v1/streams/{geo_id}/offers", json={"offer_id": 3717})
    assert r.status_code == 422


async def test_sync_imports_external_changes(client, keitaro, campaign):
    sid = await _stream(campaign)
    # somebody edited the stream directly in Keitaro
    keitaro.streams[sid]["offers"] = [
        {"offer_id": 3717, "share": 70, "state": "active"},
        {"offer_id": 3910, "share": 30, "state": "active"},
    ]
    await client.post(f"/api/v1/streams/{sid}/offers", json={"offer_id": 3801})  # local draft
    r = await client.post(f"/api/v1/campaigns/{campaign['id']}/sync")
    stream = offers_stream(r.json())
    assert shares(stream) == {3717: 70, 3910: 30}
    by_id = {o["offer_id"]: o for o in stream["offers"]}
    assert by_id[3749]["status"] == "removed"  # was published → archived
    assert 3801 not in by_id  # unpublished draft dropped
    assert stream["is_dirty"] is False


async def test_open_campaign_created_outside_tool(client, keitaro):
    remote = await keitaro.create_campaign({"name": "manual", "alias": "abc", "domain_id": 1813, "state": "active"})
    await keitaro.create_stream({"campaign_id": remote["id"], "schema": "landings", "position": 1,
                                 "offers": [{"offer_id": 3749, "share": 100, "state": "active"}]})
    listing = (await client.get("/api/v1/campaigns")).json()
    assert listing[0]["id"] == remote["id"] and listing[0]["is_local"] is False
    r = await client.get(f"/api/v1/campaigns/{remote['id']}")
    assert r.status_code == 200
    data = r.json()
    assert data["origin"] == "import" and data["url"] == "https://kylovoa.com/abc"
    assert shares(data["streams"][0]) == {3749: 100}
