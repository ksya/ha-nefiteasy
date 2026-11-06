"""Tests of the Bosch session handling against a fake backend.

The NefitConnection tests need no Home Assistant instance; the last few go
through the coordinator, as Home Assistant drives it.
"""

from __future__ import annotations

import asyncio
import time
from unittest.mock import patch

from homeassistant.core import HomeAssistant
import pytest

from custom_components.nefiteasy import connection as conn
from custom_components.nefiteasy.connection import NefitConnection, NefitNotConnected
from custom_components.nefiteasy.const import (
    STATE_CONNECTION_VERIFIED,
    STATE_ERROR_AUTH,
    STATE_INIT,
)
from custom_components.nefiteasy.coordinator import NefitEasy

from .bosch_fake import Backend

CONFIG = {"serial": "123456789", "accesskey": "myAccessKey", "password": "myPass"}
URL = "/system/appliance/systemPressure"


@pytest.fixture
def backend(monkeypatch):
    """Provide a fake backend, with timeouts short enough for tests."""
    fake = Backend()
    monkeypatch.setattr(conn, "CONNECT_TIMEOUT", 0.2)
    monkeypatch.setattr(conn, "REQUEST_TIMEOUT", 0.1)
    monkeypatch.setattr(conn, "TEARDOWN_TIMEOUT", 0.1)
    with patch.object(conn, "NefitCore", side_effect=fake.core), patch.object(
        NefitConnection, "_async_backend_reachable", new=fake.reachable
    ):
        yield fake


class Recorder:
    """Callbacks for a NefitConnection, counting what they were told."""

    def __init__(self) -> None:
        """Nothing seen yet."""
        self.messages: list[dict] = []
        self.sessions_lost = 0
        self.auth_failures: list[str] = []
        self.connection: NefitConnection | None = None

    async def message(self, data: dict) -> None:
        """Store the message and wake the request waiting for it."""
        self.messages.append(data)
        assert self.connection is not None
        self.connection.resolve(data["id"])

    def session_lost(self) -> None:
        """Count a lost session."""
        self.sessions_lost += 1

    async def auth_failed(self, event: str) -> None:
        """Record a failed login."""
        self.auth_failures.append(event)


def new_connection() -> tuple[NefitConnection, Recorder]:
    """Create a connection wired to a Recorder."""
    rec = Recorder()
    connection = NefitConnection(CONFIG, rec.message, rec.session_lost, rec.auth_failed)
    rec.connection = connection
    return connection, rec


async def poll(connection: NefitConnection) -> bool:
    """One poll cycle as the coordinator does it; True if it succeeded.

    A request without a reply means reconnecting and retrying once.
    """
    try:
        await connection.async_ensure_connected()
    except NefitNotConnected:
        return False
    try:
        await connection.async_get(URL)
        return True
    except asyncio.TimeoutError:
        connection.mark_lost()
    try:
        await connection.async_ensure_connected()
        await connection.async_get(URL)
    except (NefitNotConnected, asyncio.TimeoutError):
        connection.mark_lost()
        return False
    return True


async def test_connect_and_get(backend: Backend) -> None:
    """A normal login is verified and a GET gets its reply."""
    connection, rec = new_connection()
    await connection.connect()
    assert connection.connected_state == STATE_CONNECTION_VERIFIED
    await connection.async_get(URL)
    assert rec.messages[-1]["id"] == URL
    assert len(backend.live_clients()) == 1
    await connection.shutdown("test")
    assert backend.live_clients() == []


async def test_reconnect_uses_a_fresh_client(backend: Backend) -> None:
    """Each connect replaces the client and closes the old one completely."""
    connection, _ = new_connection()
    await connection.connect()
    old = connection.nefit
    await connection.connect()
    assert connection.nefit is not old
    assert old.xmppclient.aborted
    assert old.xmppclient._run_out_filters.cancelled
    assert old.message_callback is None and old.session_end_callback is None
    assert len(backend.live_clients()) == 1


async def test_stale_client_callbacks_ignored(backend: Backend) -> None:
    """A session_end from a replaced client doesn't touch the current session."""
    connection, rec = new_connection()
    await connection.connect()
    old = connection.nefit
    await connection.connect()
    old.end_session()
    await asyncio.sleep(0.05)
    assert connection.connected_state == STATE_CONNECTION_VERIFIED
    assert rec.sessions_lost == 0


async def test_session_end_reported_once(backend: Backend) -> None:
    """A duplicate session_end for the same session is reported only once."""
    connection, rec = new_connection()
    await connection.connect()
    connection.nefit.end_session()
    connection.nefit.end_session()
    await asyncio.sleep(0.05)
    assert connection.connected_state == STATE_INIT
    assert rec.sessions_lost == 1


async def test_shutdown_interrupts_connect(backend: Backend) -> None:
    """Shutdown during a connect doesn't wait for the connect to time out."""
    connection, _ = new_connection()
    backend.mode = "silent"  # logs in, but the test request gets no reply
    task = asyncio.get_running_loop().create_task(connection.connect())
    await asyncio.sleep(0.03)
    start = time.monotonic()
    await connection.shutdown("test")
    await task
    assert time.monotonic() - start < conn.CONNECT_TIMEOUT
    assert connection.connected_state != STATE_CONNECTION_VERIFIED
    assert backend.live_clients() == []
    assert not await poll(connection)
    assert backend.connect_attempts == 1, "no reconnect after shutdown"


async def test_auth_failure_stops_retrying(backend: Backend) -> None:
    """Bad credentials are reported once and not retried."""
    connection, rec = new_connection()
    backend.mode = "auth_fail"
    await connection.connect()
    await asyncio.sleep(0.01)
    assert connection.connected_state == STATE_ERROR_AUTH
    assert rec.auth_failures == ["auth_error_password"]
    assert backend.live_clients() == []
    for _ in range(3):
        assert not await poll(connection)
    assert backend.connect_attempts == 1


async def test_unreachable_backend_skips_login(backend: Backend) -> None:
    """With TCP connections refused there is no login, and no backoff either."""
    connection, _ = new_connection()
    backend.mode = "down"
    for _ in range(5):
        assert not await poll(connection)
    assert backend.connect_attempts == 0
    assert backend.tcp_checks == 5
    backend.mode = "up"
    assert await poll(connection)
    assert backend.connect_attempts == 1


async def test_failed_logins_back_off_with_jitter(
    backend: Backend, monkeypatch
) -> None:
    """Logins that fail with the backend reachable wait 1, 2, 4, 8, 10... min."""
    monkeypatch.setattr(conn, "CONNECT_TIMEOUT", 0.02)
    connection, _ = new_connection()
    backend.mode = "silent"
    delays = []
    for _ in range(7):
        assert not await poll(connection)
        delays.append(connection._next_login - time.monotonic())
        connection._next_login = 0.0  # pretend the wait has passed
    assert backend.connect_attempts == 7
    for delay, nominal in zip(delays, [60, 120, 240, 480, 600, 600, 600]):
        assert 0.74 * nominal <= delay <= 1.26 * nominal, delays

    # While a wait is pending, a poll fails at once without a login.
    connection._next_login = time.monotonic() + 600
    assert not await poll(connection)
    assert backend.connect_attempts == 7

    # A successful login resets the backoff.
    backend.mode = "up"
    connection._next_login = 0.0
    assert await poll(connection)
    assert connection._login_failures == 0 and connection._next_login == 0.0


@pytest.mark.parametrize("mode", ["down", "silent", "raise"])
async def test_long_outage_then_recovery(
    backend: Backend, monkeypatch, mode: str
) -> None:
    """Through a long outage no session or task piles up, and it recovers at once."""
    connection, _ = new_connection()
    await connection.connect()
    monkeypatch.setattr(conn, "CONNECT_TIMEOUT", 0.02)
    monkeypatch.setattr(conn, "REQUEST_TIMEOUT", 0.01)
    tasks_before = len(asyncio.all_tasks())
    backend.mode = mode
    for _ in range(30):
        assert not await poll(connection)
        assert backend.live_clients() == []
        assert connection.connected_state == STATE_INIT
        connection._next_login = 0.0  # skip the login backoff
    await asyncio.sleep(0.05)
    assert len(asyncio.all_tasks()) <= tasks_before + 1

    monkeypatch.setattr(conn, "CONNECT_TIMEOUT", 0.2)
    monkeypatch.setattr(conn, "REQUEST_TIMEOUT", 0.1)
    backend.mode = "up"
    assert await poll(connection)
    assert len(backend.live_clients()) == 1


async def test_slow_backend_connects_and_polls(backend: Backend, monkeypatch) -> None:
    """A backend answering each step after 7 s still works (run at 1/100 scale).

    Measured: when degraded, Bosch answered every XMPP step after 4-9 s, so a
    login took 50-60 s. The real timeouts, scaled the same way, must allow it.
    """
    scale = 0.01
    monkeypatch.setattr(conn, "CONNECT_TIMEOUT", 90.0 * scale)
    monkeypatch.setattr(conn, "REQUEST_TIMEOUT", 20.0 * scale)
    backend.step_latency = 7.0 * scale
    connection, _ = new_connection()
    await connection.connect()
    assert connection.connected_state == STATE_CONNECTION_VERIFIED
    for _ in range(8):
        await connection.async_get(URL)
    assert backend.connect_attempts == 1


async def test_setup_retries_leave_no_sessions(backend: Backend, monkeypatch) -> None:
    """Failed setups (a new connection each time, then shutdown) leave nothing open."""
    monkeypatch.setattr(conn, "CONNECT_TIMEOUT", 0.02)
    backend.mode = "silent"
    for _ in range(10):
        connection, _ = new_connection()
        await connection.connect()
        assert connection.connected_state == STATE_INIT
        await connection.shutdown("Setup failed")
    assert backend.live_clients() == []


async def _heal_after(backend: Backend, delay: float) -> None:
    await asyncio.sleep(delay)
    backend.mode = "up"


async def test_silent_drop_recovers_within_one_update(
    hass: HomeAssistant, backend: Backend
) -> None:
    """A request without a reply makes the update reconnect and retry, not fail."""
    coordinator = NefitEasy(hass, CONFIG)
    await coordinator.connection.connect()
    first = coordinator.nefit
    backend.mode = "silent"
    heal = hass.async_create_task(_heal_after(backend, 0.05))
    await coordinator.async_refresh()
    await heal
    assert coordinator.last_update_success
    assert coordinator.nefit is not first and first.xmppclient.aborted
    assert len(backend.live_clients()) == 1
    await coordinator.connection.shutdown("test")


async def test_concurrent_updates_are_serialised(
    hass: HomeAssistant, backend: Backend
) -> None:
    """Overlapping updates don't replace each other's session."""
    coordinator = NefitEasy(hass, CONFIG)
    await coordinator.connection.connect()
    backend.mode = "silent"
    heal = hass.async_create_task(_heal_after(backend, 0.05))
    await asyncio.gather(
        coordinator._async_update_data(),
        coordinator._async_update_data(),
        coordinator._async_update_data(),
    )
    await heal
    assert len(backend.live_clients()) == 1
    await coordinator.connection.shutdown("test")
