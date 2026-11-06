"""Connection to the Bosch cloud for a Nefit Easy thermostat.

Owns the XMPP session with the Bosch cloud: connecting, verifying the
connection, matching a reply to the request waiting for it, and the session
callbacks. It uses no Home Assistant APIs, so it can be tested without a
running Home Assistant; the coordinator is told about session events through
the callbacks passed in.

Exactly one session exists at a time. Every (re)connect gets a brand new
NefitCore and the previous one is torn down fully. Before each login the
backend is checked for TCP connections, and failed logins back off with
jitter.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
import logging
import random
import time
from typing import Any

from aionefit import NefitCore
import slixmpp

from .const import (
    CONF_ACCESSKEY,
    CONF_PASSWORD,
    CONF_SERIAL,
    STATE_CONNECTED,
    STATE_CONNECTION_VERIFIED,
    STATE_ERROR_AUTH,
    STATE_INIT,
)

_LOGGER = logging.getLogger(__name__)

# When the backend is degraded it stays reachable but answers slowly: on
# 2026-11-03 each XMPP step took 4-9 s and a login timed out 0.2 s before its
# last reply arrived; a login is about 8 round trips. GET replies have been
# measured at up to 20 s, while still being answered. Normally both take well
# under a second, so the larger limits only cost time when the backend is
# unreachable.
CONNECT_TIMEOUT = 90.0
REQUEST_TIMEOUT = 20.0
TEARDOWN_TIMEOUT = 5.0

# Reachability check before each login. 10 s covers four TCP SYNs (Linux
# retries after 1, 3 and 7 s), which matters when the backend accepts only a
# few connections.
BOSCH_HOST = "wa2-mz36-qrmzh6.bosch.de"  # aionefit's default
BOSCH_PORT = 5222
REACHABLE_TIMEOUT = 10.0
# After a failed login with the backend reachable (it accepts the connection
# but doesn't complete the login), wait 1, 2, 4, 8, then 10 minutes between
# attempts, +/-25 % so that installations don't all retry in step. A failed TCP
# check is cheap for the backend and doesn't count: it is repeated every cycle
# and the login follows as soon as the backend accepts connections again.
LOGIN_BACKOFF_BASE = 60.0
LOGIN_BACKOFF_MAX = 10 * 60.0
LOGIN_BACKOFF_JITTER = 0.25


class NefitNotConnected(Exception):
    """No verified session, and none could be made now."""


class NefitConnection:
    """XMPP session with the Bosch cloud for one thermostat."""

    def __init__(
        self,
        config: dict[str, Any],
        message_callback: Callable[[dict[str, Any]], Awaitable[None]],
        session_lost_callback: Callable[[], None],
        auth_failed_callback: Callable[[str], Awaitable[None]],
    ) -> None:
        """Create the client; call connect() to start the session."""
        self.connected_state = STATE_INIT
        self.expected_end = False
        self.serial = config[CONF_SERIAL]

        self._config = config
        self._message_callback = message_callback
        self._session_lost_callback = session_lost_callback
        self._auth_failed_callback = auth_failed_callback

        self._event = asyncio.Event()
        self._request: str = ""
        self._connect_lock = asyncio.Lock()
        self._login_failures = 0
        self._next_login = 0.0  # monotonic; no login attempt before this
        self._unreachable_since: float | None = None

        # slixmpp's connect() on a client that still has a transport opens a
        # second TCP connection into the same protocol object; the two then
        # corrupt each other's parser state and replies are dropped ("Received
        # data before the connection is established"). A fresh client per
        # session rules that out.
        self.nefit = self._new_client()

    @property
    def verified(self) -> bool:
        """Whether the session is connected and has answered a request."""
        return self.connected_state == STATE_CONNECTION_VERIFIED

    @property
    def is_connecting(self) -> bool:
        """Return True while a connection attempt is in progress."""
        return self._connect_lock.locked()

    def _new_client(self) -> NefitCore:
        """Create a NefitCore whose callbacks are ignored once it is replaced."""

        # Each wrapper checks it still belongs to the current client, so a late
        # message or session_end from a replaced session cannot change our state.
        async def message_callback(data: dict[str, Any]) -> None:
            if nefit is self.nefit:
                await self._message_callback(data)

        nefit = NefitCore(
            serial_number=self._config[CONF_SERIAL],
            access_key=self._config[CONF_ACCESSKEY],
            password=self._config[CONF_PASSWORD],
            message_callback=message_callback,
        )

        async def failed_auth_handler(event: str) -> None:
            if nefit is self.nefit:
                await self.failed_auth_handler(event)

        async def session_end_callback() -> None:
            if nefit is self.nefit:
                await self.session_end_callback()

        nefit.failed_auth_handler = failed_auth_handler
        nefit.no_content_callback = self.no_content_callback
        nefit.session_end_callback = session_end_callback
        return nefit

    async def _async_teardown_client(self, nefit: NefitCore) -> None:
        """Close a client completely so nothing of its session survives."""

        async def _ignore(*args: Any) -> None:
            return None

        # Detach first: a dying session must not touch our state.
        nefit.message_callback = None
        nefit.session_end_callback = None
        nefit.failed_auth_handler = _ignore
        nefit.no_content_callback = _ignore

        xmpp = nefit.xmppclient
        try:
            # Stops slixmpp's own endless background reconnect loop; we own retries.
            xmpp.cancel_connection_attempt()
            if xmpp.transport is not None:
                # aionefit's disconnect() drops slixmpp's future; await it ourselves.
                await asyncio.wait_for(
                    xmpp.disconnect(wait=2.0, ignore_send_queue=True),
                    timeout=TEARDOWN_TIMEOUT,
                )
        except asyncio.CancelledError:
            raise
        except Exception as ex:  # noqa: BLE001 - teardown must never fail
            _LOGGER.debug("Error while closing Bosch session: %r", ex)
        finally:
            xmpp.abort()
            # Cancel the stream's filter task explicitly; left pending it is later
            # garbage collected with "Task was destroyed but it is pending!".
            run_out_filters = getattr(xmpp, "_run_out_filters", None)
            if run_out_filters is not None and not run_out_filters.done():
                run_out_filters.cancel()

    async def connect(self) -> None:
        """Replace the current session with a new, verified one."""
        # Callers queue on the lock rather than returning early, so whoever asked
        # for a connection sees the outcome of a real attempt.
        async with self._connect_lock:
            if self.expected_end:
                _LOGGER.debug("Not connecting: client is shutting down.")
                return

            _LOGGER.debug("Start connecting.")
            # Swap in the new client before closing the old one, so the old one's
            # callbacks are already ignored while it shuts down.
            old = self.nefit
            self.nefit = self._new_client()
            self.connected_state = STATE_INIT
            await self._async_teardown_client(old)

            nefit = self.nefit
            # When its backend is down, Bosch's servers often don't accept TCP
            # connections at all (the connect times out). A plain TCP connect
            # tells us that in seconds; a full login attempt would wait
            # CONNECT_TIMEOUT.
            reachable = await self._async_backend_reachable()
            if reachable:
                await self._async_login(nefit)

            if self.verified:
                self._login_failures = 0
                self._next_login = 0.0
                _LOGGER.debug("Successfully verified connection.")
                return

            if (
                reachable
                and not self.expected_end
                and self.connected_state != STATE_ERROR_AUTH
            ):
                self._login_failures += 1
                delay = min(
                    LOGIN_BACKOFF_MAX,
                    LOGIN_BACKOFF_BASE * 2 ** (self._login_failures - 1),
                ) * random.uniform(1 - LOGIN_BACKOFF_JITTER, 1 + LOGIN_BACKOFF_JITTER)
                self._next_login = time.monotonic() + delay
                _LOGGER.debug(
                    "Login attempt %s failed; next attempt in %.0f s",
                    self._login_failures,
                    delay,
                )

            # Failed (backend unreachable, no response or bad credentials): close
            # this attempt so no half-open session lingers until the next try.
            # Keep an auth error visible so updates stop retrying until reauth.
            if self.connected_state != STATE_ERROR_AUTH:
                self.connected_state = STATE_INIT
            await self._async_teardown_client(nefit)

    async def _async_login(self, nefit: NefitCore) -> None:
        """Log in and check that the session answers a request."""
        # Events from a previous session may still be set; clear them so the
        # waits below only return for this session's handshake.
        nefit.xmppclient.connected_event.clear()
        nefit.xmppclient.message_event.clear()
        try:
            await nefit.connect()
            _LOGGER.debug("Waiting for connected event.")
            await asyncio.wait_for(
                nefit.xmppclient.connected_event.wait(), timeout=CONNECT_TIMEOUT
            )
        except asyncio.TimeoutError:
            _LOGGER.debug("TimeoutError on waiting for connected event.")
        except asyncio.CancelledError:
            await self._async_teardown_client(nefit)
            raise
        except Exception as ex:  # noqa: BLE001 - treat like an unreachable backend
            # Escaping here would turn a network outage into a setup error, which
            # Home Assistant does not retry; fail the attempt like a timeout.
            _LOGGER.debug("Error starting connection: %r", ex)
        else:
            if self.connected_state == STATE_INIT and not self.expected_end:
                _LOGGER.debug("Connected successfully.")
                self.connected_state = STATE_CONNECTED

        if self.connected_state != STATE_CONNECTED or self.expected_end:
            return

        try:
            nefit.get("/gateway/brandID")
            _LOGGER.debug("Wait for message event")
            await asyncio.wait_for(
                nefit.xmppclient.message_event.wait(), timeout=CONNECT_TIMEOUT
            )
        except slixmpp.xmlstream.xmlstream.NotConnectedError:
            _LOGGER.debug("Connection lost while testing connection.")
        except asyncio.TimeoutError:
            _LOGGER.debug("Did not get a response in time for testing connection.")
        else:
            _LOGGER.debug("Message event received")
            nefit.xmppclient.message_event.clear()

            # No exception, no auth error and not shutting down
            if self.connected_state == STATE_CONNECTED and not self.expected_end:
                self.connected_state = STATE_CONNECTION_VERIFIED

    async def _async_backend_reachable(self) -> bool:
        """Whether the backend accepts a TCP connection (closed straight away)."""
        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(BOSCH_HOST, BOSCH_PORT),
                timeout=REACHABLE_TIMEOUT,
            )
        except (OSError, asyncio.TimeoutError) as ex:
            if self._unreachable_since is None:
                self._unreachable_since = time.monotonic()
                _LOGGER.info("Bosch backend not accepting connections (%r)", ex)
            return False
        writer.close()
        try:
            await writer.wait_closed()
        except OSError:
            pass
        if self._unreachable_since is not None:
            _LOGGER.info(
                "Bosch backend accepting connections again after %.0f min",
                (time.monotonic() - self._unreachable_since) / 60,
            )
            self._unreachable_since = None
        return True

    async def async_ensure_connected(self) -> None:
        """Have a verified session, connecting if needed; raise if there is none."""
        if self.connected_state == STATE_ERROR_AUTH:
            raise NefitNotConnected("authentication failed, reauth required")
        if self.verified:
            return
        if time.monotonic() < self._next_login:
            raise NefitNotConnected(
                "waiting "
                f"{self._next_login - time.monotonic():.0f} s before the next login"
            )
        _LOGGER.debug("Starting reconnect procedure.")
        await self.connect()
        if not self.verified:
            raise NefitNotConnected("not connected")

    def mark_lost(self) -> None:
        """Forget the session after a request failed; the next update reconnects."""
        if self.connected_state != STATE_ERROR_AUTH:
            self.connected_state = STATE_INIT

    async def shutdown(self, event: str) -> None:
        """Close the session for good."""
        _LOGGER.debug("Shutdown connection to Bosch cloud: %s", event)
        self.expected_end = True
        self.connected_state = STATE_INIT
        nefit = self.nefit
        # Release a connect() that is waiting on this session so it finishes
        # straight away (it checks expected_end) instead of sitting out its
        # timeouts.
        nefit.xmppclient.connected_event.set()
        nefit.xmppclient.message_event.set()
        await self._async_teardown_client(nefit)
        async with self._connect_lock:
            # connect() may have swapped in a newer client meanwhile; close that too.
            if self.nefit is not nefit:
                await self._async_teardown_client(self.nefit)

    async def no_content_callback(self, data: Any) -> None:
        """Log no content."""
        _LOGGER.debug("no_content_callback: %s", data)

    async def failed_auth_handler(self, event: str) -> None:
        """Handle failed auth."""
        self.connected_state = STATE_ERROR_AUTH
        # Unblock connect(); it sees the auth error and closes the session itself.
        # (Calling shutdown() from here would wait on the connect lock that the
        # waiting connect() holds.)
        self.nefit.xmppclient.connected_event.set()
        self.nefit.xmppclient.message_event.set()

        await self._auth_failed_callback(event)

    async def session_end_callback(self) -> None:
        """If a verified session is closed unexpectedly, report it."""
        # Only a verified session can "end": during connect() the state is INIT
        # or CONNECTED and connect() handles failure itself. This also makes a
        # duplicate session_end for the same session a no-op.
        if not self.expected_end and self.verified:
            _LOGGER.debug(
                "Unexpected disconnect of %s with Bosch server. Try to reconnect..",
                self.serial,
            )
            self.connected_state = STATE_INIT
            self._session_lost_callback()

    def resolve(self, path: str) -> bool:
        """Wake the request waiting for path; False if nothing was waiting for it."""
        if self._request != path:
            return False
        self._event.set()
        return True

    async def async_get(self, url: str) -> None:
        """Request url and wait until its reply has been handled (see resolve)."""
        self._event.clear()
        self._request = url
        self.nefit.get(url)
        try:
            await asyncio.wait_for(self._event.wait(), timeout=REQUEST_TIMEOUT)
        finally:
            self._request = ""

    def get_quietly(self, url: str) -> None:
        """Request url without waiting; skip it if there is no session."""
        try:
            self.nefit.get(url)
        except slixmpp.xmlstream.xmlstream.NotConnectedError:
            _LOGGER.debug("Skipped GET %s: not connected", url)
