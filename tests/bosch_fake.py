"""A fake Bosch backend and NefitCore that model the backend's failure modes.

Modes: "up" (normal), "down" (TCP connections refused), "silent" (connects and
logs in, but requests get no reply, like a session Bosch dropped without
telling us), "raise" (the client library raises from connect()) and
"auth_fail" (bad credentials).
"""

from __future__ import annotations

import asyncio
from typing import Any

import slixmpp


class Backend:
    """State of the fake backend, shared by every client created from it."""

    def __init__(self) -> None:
        """Start up and empty."""
        self.mode = "up"
        self.step_latency = 0.0  # extra delay per server round trip
        self.connect_attempts = 0
        self.tcp_checks = 0
        self.gets: list[str] = []
        self.clients: list[FakeNefitCore] = []

    def core(self, **kwargs: Any) -> FakeNefitCore:
        """Create a client, as NefitCore(...) would (use as the patch side_effect)."""
        client = FakeNefitCore(self, **kwargs)
        self.clients.append(client)
        return client

    async def reachable(self, *args: Any) -> bool:
        """Stand-in for NefitConnection._async_backend_reachable."""
        self.tcp_checks += 1
        return self.mode != "down"

    def live_clients(self) -> list[FakeNefitCore]:
        """Clients whose session is still open or still trying to connect."""
        return [c for c in self.clients if c.xmppclient.live()]


class FakeTask:
    """Stands in for slixmpp's output filter task."""

    def __init__(self) -> None:
        """Start running."""
        self.cancelled = False

    def done(self) -> bool:
        """Whether the task has finished."""
        return self.cancelled

    def cancel(self) -> None:
        """Cancel the task."""
        self.cancelled = True


class FakeXmpp:
    """The parts of slixmpp's ClientXMPP that the integration uses."""

    def __init__(self) -> None:
        """Not connected."""
        self.connected_event = asyncio.Event()
        self.message_event = asyncio.Event()
        self.transport: object | None = None
        self.aborted = False
        self.attempting = False
        self._run_out_filters: FakeTask | None = None
        self.connect_calls = 0

    def cancel_connection_attempt(self) -> None:
        """Stop trying to connect."""
        self.attempting = False

    def disconnect(self, wait: float = 2.0, ignore_send_queue: bool = False):
        """Close the stream; returns a future like slixmpp does."""
        fut = asyncio.get_running_loop().create_future()
        self.transport = None
        fut.set_result(None)
        return fut

    def abort(self) -> None:
        """Drop the connection at once."""
        self.aborted = True
        self.transport = None
        self.attempting = False

    def live(self) -> bool:
        """Whether this session is still open or connecting."""
        return (self.transport is not None or self.attempting) and not self.aborted


class FakeNefitCore:
    """The parts of aionefit's NefitCore that the integration uses."""

    def __init__(
        self,
        backend: Backend,
        serial_number: str,
        access_key: str,
        password: str,
        message_callback: Any = None,
    ) -> None:
        """Create a client for backend."""
        self.backend = backend
        self.serial_number = serial_number
        self.message_callback = message_callback
        self.failed_auth_handler: Any = None
        self.no_content_callback: Any = None
        self.session_end_callback: Any = None
        self.xmppclient = FakeXmpp()

    async def connect(self) -> None:
        """Start logging in; the connected event follows after the round trips."""
        xmpp = self.xmppclient
        xmpp.connect_calls += 1
        assert xmpp.connect_calls == 1, "connect() reused on the same client"
        self.backend.connect_attempts += 1
        if self.backend.mode == "raise":
            raise OSError("Network is unreachable")
        xmpp._run_out_filters = FakeTask()
        xmpp.attempting = True
        loop = asyncio.get_running_loop()

        def established() -> None:
            if xmpp.aborted or self.backend.mode == "down":
                return
            xmpp.transport = object()
            xmpp.attempting = False
            if self.backend.mode == "auth_fail":
                loop.create_task(self.failed_auth_handler("auth_error_password"))
            else:
                xmpp.connected_event.set()

        # A login is about 8 round trips (stream, STARTTLS, TLS, stream, SASL x2,
        # bind, session).
        loop.call_later(0.01 + 8 * self.backend.step_latency, established)

    async def disconnect(self) -> None:
        """Close the session."""
        self.xmppclient.disconnect()

    def get(self, url: str) -> None:
        """Send a GET; the reply arrives later through message_callback."""
        xmpp = self.xmppclient
        if xmpp.transport is None:
            raise slixmpp.xmlstream.xmlstream.NotConnectedError()
        self.backend.gets.append(url)
        if self.backend.mode != "up":
            return  # silently dropped session: the request vanishes

        async def reply() -> None:
            await asyncio.sleep(0.005 + self.backend.step_latency)
            if xmpp.aborted or xmpp.transport is None:
                return
            data: dict[str, Any] = {"id": url, "value": 1}
            if url == "/ecus/rrc/uiStatus":
                data["value"] = {
                    "TSP": "20",
                    "IHT": "19.5",
                    "UMD": "clock",
                    "BAI": "No",
                    "CTD": "now",
                }
            if self.message_callback:
                await self.message_callback(data)
            xmpp.message_event.set()

        asyncio.get_running_loop().create_task(reply())

    def end_session(self) -> None:
        """Server closes the stream cleanly (session_end fires)."""
        self.xmppclient.transport = None
        if self.session_end_callback:
            asyncio.get_running_loop().create_task(self.session_end_callback())
