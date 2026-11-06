"""Synchronous acceptance client for the bounded message acknowledgement contract."""

import time

from fastapi.testclient import TestClient


class TextPollingClient(TestClient):
    """Wait for final message outcomes in legacy scenario drivers, not latency tests."""

    def post(self, url, **kwargs):
        result = super().post(url, **kwargs)
        deadline = time.monotonic() + 110
        while result.status_code == 202 and result.json().get("status_url"):
            if time.monotonic() >= deadline:
                raise TimeoutError("Message saved but final result exceeded 110 seconds")
            time.sleep(.25)
            result = self.get(result.json()["status_url"])
        return result
