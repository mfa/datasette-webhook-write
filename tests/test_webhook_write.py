import asyncio
import copy
import datetime
import hashlib
import hmac
import json

import httpx
import pytest
from datasette.app import Datasette


@pytest.mark.asyncio
async def test_plugin_is_installed():
    datasette = Datasette([], memory=True)
    response = await datasette.client.get("/-/plugins.json")
    assert response.status_code == 200
    installed_plugins = {p["name"] for p in response.json()}
    assert "datasette-webhook-write" in installed_plugins


TEST_SECRET = "abc123"
TEST_DATABASE_NAME = "test"
TEST_METADATA = {
    "plugins": {
        "datasette-webhook-write": {
            "webhook_secret": TEST_SECRET,
            "http_header_name": "x-signature",
            "database_name": TEST_DATABASE_NAME,
            "table_name": "table1",
        }
    }
}


@pytest.fixture
def db_path(tmp_path_factory):
    db_directory = tmp_path_factory.mktemp("dbs")
    return db_directory / (TEST_DATABASE_NAME + ".db")


@pytest.fixture
def ds(db_path):
    ds = Datasette([db_path], metadata=TEST_METADATA)
    return ds


@pytest.fixture
def ds_sha256(db_path):
    metadata = copy.deepcopy(TEST_METADATA)
    metadata["plugins"]["datasette-webhook-write"]["digestmod"] = "sha256"
    ds = Datasette([db_path], metadata=metadata)
    return ds


@pytest.mark.asyncio
async def test_get_is_not_allowed(ds):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=ds.app())) as client:
        response = await client.get("http://localhost/-/webhook-write/")
        assert response.json() == {"error": "only POST is allowed", "status": 400}
        assert 400 == response.status_code


@pytest.mark.asyncio
async def test_settings_missing():
    # FIXME: test for all setting names, not only the first one
    ds = Datasette([], memory=True)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=ds.app())) as client:
        response = await client.post("http://localhost/-/webhook-write/")
        assert response.json() == {
            "error": ">webhook_secret< needs to be configured in metadata.",
            "status": 500,
        }
        assert 500 == response.status_code


@pytest.mark.asyncio
async def test_malformed_json(ds):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=ds.app())) as client:
        response = await client.post("http://localhost/-/webhook-write/")
        assert response.json() == {"error": "wrong format", "status": 400}
        assert 400 == response.status_code


@pytest.fixture(name="document")
def document_future():
    return {"uid": 1, "category": "cat1", "data": "abc"}


@pytest.fixture(name="document2")
def document2_fixture(document):
    d = copy.copy(document)
    d["text_modified"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    return d


def calculate_signature(data):
    digest = hmac.new(
        key=TEST_SECRET.encode(),
        msg=json.dumps(
            data, ensure_ascii=False, separators=(",", ":"), allow_nan=False
        ).encode("utf-8"),
        digestmod=hashlib.sha1,
    )
    return {
        "X-SIGNATURE": f"sha1={digest.hexdigest()}",
    }


def calculate_signature_sha256(data):
    digest = hmac.new(
        key=TEST_SECRET.encode(),
        msg=json.dumps(
            data, ensure_ascii=False, separators=(",", ":"), allow_nan=False
        ).encode("utf-8"),
        digestmod=hashlib.sha256,
    )
    return {
        "X-SIGNATURE": f"{digest.hexdigest()}",
    }


@pytest.fixture()
def signature(document):
    return calculate_signature(document)


@pytest.fixture()
def signature2(document2):
    return calculate_signature(document2)


@pytest.fixture()
def signature_sha256(document):
    return calculate_signature_sha256(document)


@pytest.mark.asyncio
async def test_no_signature(ds, document):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=ds.app())) as client:
        response = await client.post("http://localhost/-/webhook-write/", json=document)
        assert response.json() == {"error": "Permission denied", "status": 403}
        assert 403 == response.status_code


@pytest.mark.asyncio
async def test_wrong_signature(ds, document, signature):
    signature["X-SIGNATURE"] = "wrong"
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=ds.app())) as client:
        response = await client.post(
            "http://localhost/-/webhook-write/", json=document, headers=signature
        )
        assert response.json() == {"error": "Permission denied", "status": 403}
        assert 403 == response.status_code


@pytest.mark.asyncio
async def test_actual_write(ds, document, signature):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=ds.app())) as client:
        response = await client.post(
            "http://localhost/-/webhook-write/", json=document, headers=signature
        )
        assert 200 == response.status_code

        # check if write was successful
        response = await client.get("http://localhost/test/table1.json?_shape=array")
        data = response.json()[0]

        # test if text_modified was added
        assert data.get("text_modified")
        assert data["text_modified"].startswith("20")

        # rowid is only set, when no "pk" was set
        # text_modified is added if not exisiting in document
        data.pop("rowid")
        data.pop("text_modified")
        assert data == document


@pytest.mark.asyncio
async def test_actual_write_sha256(ds_sha256, document, signature_sha256):
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=ds_sha256.app())
    ) as client:
        response = await client.post(
            "http://localhost/-/webhook-write/", json=document, headers=signature_sha256
        )
        assert 200 == response.status_code

        # check if write was successful
        response = await client.get("http://localhost/test/table1.json?_shape=array")
        data = response.json()[0]

        # test if text_modified was added
        assert data.get("text_modified")
        assert data["text_modified"].startswith("20")

        # rowid is only set, when no "pk" was set
        # text_modified is added if not exisiting in document
        data.pop("rowid")
        data.pop("text_modified")
        assert data == document


@pytest.mark.asyncio
@pytest.mark.parametrize("pk", ("uid", ("uid", "category")))
async def test_write_replace(db_path, document2, signature2, pk):
    metadata = copy.deepcopy(TEST_METADATA)
    metadata["plugins"]["datasette-webhook-write"]["use_pk"] = pk
    ds = Datasette([db_path], metadata=metadata)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=ds.app())) as client:
        response = await client.post(
            "http://localhost/-/webhook-write/", json=document2, headers=signature2
        )
        assert 200 == response.status_code

        # check if write was successful
        response = await client.get("http://localhost/test/table1.json?_shape=array")
        data = response.json()
        assert data[0] == document2

        # replacement
        document2["data"] = "xyz"
        new_signature = calculate_signature(document2)

        response = await client.post(
            "http://localhost/-/webhook-write/", json=document2, headers=new_signature
        )
        assert 200 == response.status_code

        # check if replace was successful
        response = await client.get("http://localhost/test/table1.json?_shape=array")
        data = response.json()
        assert len(data) == 1
        assert data[0] == document2
