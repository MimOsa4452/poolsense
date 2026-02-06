"""Asynchronous Python client for PoolSense."""

from __future__ import annotations

from datetime import datetime, timezone

from aiohttp import ClientError, ClientSession

from poolsense.exceptions import PoolSenseError

BASE_URL = "https://api.poolsense.net/api/v1/"
LOGIN_URL = f"{BASE_URL}users/login"
DATA_URL = f"{BASE_URL}sigfoxData/app/"

# Hardcoded identifiers required by the PoolSense API for login.
_LOGIN_EXTRAS = {
    "uuid": "26aab38027422a59",
    "registrationId": (
        "c5tknccIS_I:APA91bF0LS4mAR2NETBJ9tNFYEbvUgileRovnuC1Y9-yTy2qDsW4"
        "_YHlDcapH7BnHWzxh74fPVJw0Y9KuM3sCVIWknSOlGu3WP0QNSFzfuhEwQ_yBujt9cS"
        "Vak0eVUo_IfmFf6rtlng_"
    ),
}


class PoolSense:
    """Main interface to the PoolSense device."""

    def __init__(
        self,
        session: ClientSession,
        email: str,
        password: str,
        device_id: str | None = None,
    ) -> None:
        self._session = session
        self._email = email
        self._password = password
        self._device_id = device_id

    async def _login(self) -> dict:
        """Authenticate with the PoolSense API and return the response data."""
        login_data = {
            "email": self._email,
            "password": self._password,
            **_LOGIN_EXTRAS,
        }
        try:
            resp = await self._session.post(LOGIN_URL, json=login_data)
        except ClientError as err:
            raise PoolSenseError(0, f"Connection error: {err}") from err

        if resp.status != 200:
            raise PoolSenseError(resp.status, "Login failed.")

        return await resp.json(content_type=None)

    async def test_poolsense_credentials(self) -> str | bool:
        """Validate credentials against the PoolSense servers.

        Returns the device serial number on success, "DEMO" if the account
        has no devices, or False if authentication fails.
        """
        try:
            data = await self._login()
        except PoolSenseError:
            return False

        if data.get("token") is None:
            return False

        if data.get("devices") and len(data["devices"]) > 0:
            return data["devices"][0]["serial"]

        return "DEMO"

    async def get_poolsense_data(self) -> dict[str, object]:
        """Fetch all sensor data for the configured device.

        Returns a dictionary with the following keys:
            Chlorine, pH, Water Temp, Chlorine Instant, pH Instant,
            Water Temp Instant, Battery, Last Seen, Chlorine High,
            Chlorine Low, pH High, pH Low, pH Status, Chlorine Status.
        """
        data = await self._login()

        serial = self._device_id or data["devices"][0]["serial"]
        url = f"{DATA_URL}{serial}/?tz=-120"
        headers = {"Authorization": f"token {data['token']}"}

        try:
            resp = await self._session.get(url, headers=headers)
        except ClientError as err:
            raise PoolSenseError(0, f"Connection error: {err}") from err

        if resp.status != 200:
            raise PoolSenseError(resp.status, "Server error.")

        data = await resp.json(content_type=None)

        # Parse the Last Seen timestamp into an ISO 8601 string so that
        # Home Assistant's TIMESTAMP device class can consume it directly.
        last_seen_raw = data.get("lastData", {}).get("time", "")
        last_seen: str | None = None
        if last_seen_raw:
            try:
                dt = datetime.strptime(last_seen_raw, "%m/%d/%Y, %I:%M:%S %p")
                last_seen = dt.replace(tzinfo=timezone.utc).isoformat()
            except (ValueError, TypeError):
                last_seen = last_seen_raw

        return {
            "Chlorine": data["ORP"],
            "pH": data["pH"],
            "Water Temp": data["waterTemp"],
            "Chlorine Instant": data["lastData"]["ORP"],
            "pH Instant": data["lastData"]["pH"],
            "Water Temp Instant": data["lastData"]["waterTemp"],
            "Battery": data["vBat"],
            "Last Seen": last_seen,
            "Chlorine High": data["display"]["orpNotificationMax"],
            "Chlorine Low": data["display"]["orpNotificationMin"],
            "pH High": data["display"]["phNotificationMax"],
            "pH Low": data["display"]["phNotificationMin"],
            "pH Status": data["display"]["pHColor"],
            "Chlorine Status": data["display"]["ORPColor"],
        }
