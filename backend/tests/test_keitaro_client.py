import httpx
import pytest

from app.core.exceptions import KeitaroError, NotFoundError
from app.integrations.keitaro.client import KeitaroClient

BASE = "https://tracker.test/admin_api/v1"


def make_client(response: httpx.Response) -> KeitaroClient:
    return KeitaroClient(BASE, "key", transport=httpx.MockTransport(lambda request: response))


async def test_json_response_is_returned():
    client = make_client(httpx.Response(200, json=[{"id": 1813, "name": "kylovoa.com"}]))
    assert await client.list_domains() == [{"id": 1813, "name": "kylovoa.com"}]
    await client.aclose()


async def test_non_json_success_response_is_keitaro_error():
    # wrong KEITARO_URL → a web page answers 200 with HTML
    client = make_client(httpx.Response(200, text="<html>login page</html>"))
    with pytest.raises(KeitaroError, match="non-JSON response") as exc:
        await client.list_domains()
    assert exc.value.status_code == 502
    await client.aclose()


async def test_404_is_not_found():
    client = make_client(httpx.Response(404, json={"error": "not found"}))
    with pytest.raises(NotFoundError):
        await client.get_campaign(1)
    await client.aclose()
