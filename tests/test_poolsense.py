"""Unit tests for the PoolSense client library."""

import pytest
import aiohttp
from aioresponses import aioresponses

from poolsense import PoolSense, LOGIN_URL, DATA_URL
from poolsense.exceptions import PoolSenseError

EMAIL = "test@example.com"
PASSWORD = "testpass"
DEVICE_SERIAL = "ABC123"

LOGIN_RESPONSE = {
    "token": "fake-token-xyz",
    "devices": [{"serial": DEVICE_SERIAL}],
}

DATA_RESPONSE = {
    "ORP": 650,
    "pH": 7.2,
    "waterTemp": 28.5,
    "vBat": 85,
    "lastData": {
        "ORP": 648,
        "pH": 7.1,
        "waterTemp": 28.3,
        "time": "01/15/2024, 02:30:45 PM",
    },
    "display": {
        "orpNotificationMax": 800,
        "orpNotificationMin": 600,
        "phNotificationMax": 7.6,
        "phNotificationMin": 7.0,
        "pHColor": "green",
        "ORPColor": "green",
    },
}


# --- Constructor tests ---


@pytest.mark.asyncio
async def test_constructor_three_args():
    """HA creates PoolSense with 3 args: session, email, password."""
    async with aiohttp.ClientSession() as session:
        ps = PoolSense(session, EMAIL, PASSWORD)
        assert ps._email == EMAIL
        assert ps._password == PASSWORD
        assert ps._device_id is None


@pytest.mark.asyncio
async def test_constructor_four_args():
    """Multi-device support: PoolSense with explicit device_id."""
    async with aiohttp.ClientSession() as session:
        ps = PoolSense(session, EMAIL, PASSWORD, device_id="DEV1")
        assert ps._device_id == "DEV1"


# --- test_poolsense_credentials tests ---


@pytest.mark.asyncio
async def test_credentials_valid():
    """Valid credentials return device serial."""
    with aioresponses() as m:
        m.post(LOGIN_URL, payload=LOGIN_RESPONSE)
        async with aiohttp.ClientSession() as session:
            ps = PoolSense(session, EMAIL, PASSWORD)
            result = await ps.test_poolsense_credentials()
            assert result == DEVICE_SERIAL


@pytest.mark.asyncio
async def test_credentials_no_devices():
    """Valid credentials but no devices returns 'DEMO'."""
    with aioresponses() as m:
        m.post(LOGIN_URL, payload={"token": "tok", "devices": []})
        async with aiohttp.ClientSession() as session:
            ps = PoolSense(session, EMAIL, PASSWORD)
            result = await ps.test_poolsense_credentials()
            assert result == "DEMO"


@pytest.mark.asyncio
async def test_credentials_no_token():
    """Response with null token returns False."""
    with aioresponses() as m:
        m.post(LOGIN_URL, payload={"token": None, "devices": []})
        async with aiohttp.ClientSession() as session:
            ps = PoolSense(session, EMAIL, PASSWORD)
            result = await ps.test_poolsense_credentials()
            assert result is False


@pytest.mark.asyncio
async def test_credentials_bad_password():
    """HTTP 401 returns False (not an exception)."""
    with aioresponses() as m:
        m.post(LOGIN_URL, status=401)
        async with aiohttp.ClientSession() as session:
            ps = PoolSense(session, EMAIL, PASSWORD)
            result = await ps.test_poolsense_credentials()
            assert result is False


@pytest.mark.asyncio
async def test_credentials_network_error():
    """Network error returns False (not an exception)."""
    with aioresponses() as m:
        m.post(LOGIN_URL, exception=aiohttp.ClientError("DNS fail"))
        async with aiohttp.ClientSession() as session:
            ps = PoolSense(session, EMAIL, PASSWORD)
            result = await ps.test_poolsense_credentials()
            assert result is False


# --- get_poolsense_data tests ---


@pytest.mark.asyncio
async def test_get_data_success():
    """Successful data fetch returns all expected keys."""
    data_url = f"{DATA_URL}{DEVICE_SERIAL}/?tz=-120"
    with aioresponses() as m:
        m.post(LOGIN_URL, payload=LOGIN_RESPONSE)
        m.get(data_url, payload=DATA_RESPONSE)
        async with aiohttp.ClientSession() as session:
            ps = PoolSense(session, EMAIL, PASSWORD)
            data = await ps.get_poolsense_data()

    expected_keys = {
        "Chlorine", "pH", "Water Temp",
        "Chlorine Instant", "pH Instant", "Water Temp Instant",
        "Battery", "Last Seen",
        "Chlorine High", "Chlorine Low", "pH High", "pH Low",
        "pH Status", "Chlorine Status",
    }
    assert set(data.keys()) == expected_keys
    assert data["Chlorine"] == 650
    assert data["pH"] == 7.2
    assert data["Water Temp"] == 28.5
    assert data["Battery"] == 85
    assert data["pH Status"] == "green"
    assert data["Chlorine Status"] == "green"


@pytest.mark.asyncio
async def test_get_data_timestamp_iso8601():
    """Last Seen timestamp is converted to ISO 8601."""
    data_url = f"{DATA_URL}{DEVICE_SERIAL}/?tz=-120"
    with aioresponses() as m:
        m.post(LOGIN_URL, payload=LOGIN_RESPONSE)
        m.get(data_url, payload=DATA_RESPONSE)
        async with aiohttp.ClientSession() as session:
            ps = PoolSense(session, EMAIL, PASSWORD)
            data = await ps.get_poolsense_data()

    last_seen = data["Last Seen"]
    # Should be ISO 8601 format: 2024-01-15T14:30:45+00:00
    assert "2024-01-15" in last_seen
    assert "T" in last_seen
    assert "14:30:45" in last_seen


@pytest.mark.asyncio
async def test_get_data_with_device_id():
    """Explicit device_id is used instead of the one from login."""
    custom_device = "CUSTOM99"
    data_url = f"{DATA_URL}{custom_device}/?tz=-120"
    with aioresponses() as m:
        m.post(LOGIN_URL, payload=LOGIN_RESPONSE)
        m.get(data_url, payload=DATA_RESPONSE)
        async with aiohttp.ClientSession() as session:
            ps = PoolSense(session, EMAIL, PASSWORD, device_id=custom_device)
            data = await ps.get_poolsense_data()

    assert data["Chlorine"] == 650


@pytest.mark.asyncio
async def test_get_data_login_failure():
    """Login failure raises PoolSenseError."""
    with aioresponses() as m:
        m.post(LOGIN_URL, status=401)
        async with aiohttp.ClientSession() as session:
            ps = PoolSense(session, EMAIL, PASSWORD)
            with pytest.raises(PoolSenseError) as exc_info:
                await ps.get_poolsense_data()
            assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_data_server_error():
    """Server error on data fetch raises PoolSenseError."""
    data_url = f"{DATA_URL}{DEVICE_SERIAL}/?tz=-120"
    with aioresponses() as m:
        m.post(LOGIN_URL, payload=LOGIN_RESPONSE)
        m.get(data_url, status=500)
        async with aiohttp.ClientSession() as session:
            ps = PoolSense(session, EMAIL, PASSWORD)
            with pytest.raises(PoolSenseError) as exc_info:
                await ps.get_poolsense_data()
            assert exc_info.value.status_code == 500


@pytest.mark.asyncio
async def test_get_data_network_error():
    """Network error during data fetch raises PoolSenseError."""
    with aioresponses() as m:
        m.post(LOGIN_URL, payload=LOGIN_RESPONSE)
        data_url = f"{DATA_URL}{DEVICE_SERIAL}/?tz=-120"
        m.get(data_url, exception=aiohttp.ClientError("timeout"))
        async with aiohttp.ClientSession() as session:
            ps = PoolSense(session, EMAIL, PASSWORD)
            with pytest.raises(PoolSenseError) as exc_info:
                await ps.get_poolsense_data()
            assert "Connection error" in exc_info.value.status


# --- PoolSenseError tests ---


def test_exception_attributes():
    """PoolSenseError stores status_code and status."""
    err = PoolSenseError(404, "Not found")
    assert err.status_code == 404
    assert err.status == "Not found"
    assert str(err) == "Not found"
