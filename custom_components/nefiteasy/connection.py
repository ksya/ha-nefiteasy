"""Connection to the Bosch cloud for a Nefit Easy thermostat.

Owns the NefitCore client and its XMPP session: connecting, verifying the
connection, matching a reply to the request waiting for it, and the session
callbacks. It uses no Home Assistant APIs, so it can be tested without a
running Home Assistant; the coordinator is told about session events through
the callbacks passed in.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
import logging
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
        self.is_connecting = False
        self.serial = config[CONF_SERIAL]

        self._event = asyncio.Event()
        self._request: str = ""
        self._session_lost_callback = session_lost_callback
        self._auth_failed_callback = auth_failed_callback

        self.nefit = NefitCore(
            serial_number=config[CONF_SERIAL],
            access_key=config[CONF_ACCESSKEY],
            password=config[CONF_PASSWORD],
            message_callback=message_callback,
        )

        self.nefit.failed_auth_handler = self.failed_auth_handler
        self.nefit.no_content_callback = self.no_content_callback
        self.nefit.session_end_callback = self.session_end_callback

    @property
    def verified(self) -> bool:
        """Whether the session is connected and has answered a request."""
        return self.connected_state == STATE_CONNECTION_VERIFIED

    async def connect(self) -> None:
        """Connect to nefit easy."""
        _LOGGER.debug("Start connecting.")
        if not self.is_connecting:
            _LOGGER.debug("Set is connecting to true")
            self.is_connecting = True
            try:
                # Events from a previous session may still be set; without
                # clearing them the waits below would return instantly and
                # verify against a dead transport. Clear BEFORE connecting
                # so a genuine handshake can set them again afterwards.
                self.nefit.xmppclient.connected_event.clear()
                self.nefit.xmppclient.message_event.clear()
                await self.nefit.connect()
                _LOGGER.debug("Waiting for connected event.")
                try:
                    await asyncio.wait_for(
                        self.nefit.xmppclient.connected_event.wait(), timeout=29.0
                    )
                except asyncio.TimeoutError:
                    _LOGGER.debug("TimeoutError on waiting for connected event.")
                except asyncio.CancelledError:
                    raise
                except Exception as ex:
                    _LOGGER.debug("Unknown error waiting for connected event: %r", ex)
                else:
                    _LOGGER.debug("Connected successfully.")
                    self.connected_state = STATE_CONNECTED

                if self.connected_state == STATE_CONNECTED:
                    try:
                        self.nefit.get("/gateway/brandID")
                    except slixmpp.xmlstream.xmlstream.NotConnectedError:
                        self.connected_state = STATE_INIT
                        return

                    try:
                        _LOGGER.debug("Wait for message event")

                        await asyncio.wait_for(
                            self.nefit.xmppclient.message_event.wait(), timeout=29.0
                        )
                    except asyncio.TimeoutError:
                        _LOGGER.debug(
                            "Did not get a response in time for testing connection."
                        )
                    except asyncio.CancelledError:
                        raise
                    except Exception as ex:
                        _LOGGER.debug("No connection while testing connection: %r", ex)
                    else:
                        _LOGGER.debug("Message event received")

                        self.nefit.xmppclient.message_event.clear()

                        # No exception and no auth error
                        if self.connected_state == STATE_CONNECTED:
                            self.connected_state = STATE_CONNECTION_VERIFIED

                if self.connected_state == STATE_CONNECTION_VERIFIED:
                    _LOGGER.debug("Successfully verified connection.")
            finally:
                _LOGGER.debug("Set is connecting to false")
                self.is_connecting = False
        else:
            _LOGGER.debug("Connection procedure is already running.")

    async def shutdown(self, event: str) -> None:
        """Shutdown."""
        _LOGGER.debug("Shutdown connection to Bosch cloud")
        self.expected_end = True
        await self.nefit.disconnect()

    async def no_content_callback(self, data: Any) -> None:
        """Log no content."""
        _LOGGER.debug("no_content_callback: %s", data)

    async def failed_auth_handler(self, event: str) -> None:
        """Handle failed auth."""
        self.connected_state = STATE_ERROR_AUTH
        self.nefit.xmppclient.connected_event.set()

        # disconnect, since nothing will work from now.
        await self.shutdown("auth_failed")

        await self._auth_failed_callback(event)

    async def session_end_callback(self) -> None:
        """If connection is closed unexpectedly, try to reconnect."""
        if not self.expected_end and self.connected_state != STATE_INIT:
            _LOGGER.debug(
                f"Unexpected disconnect of {self.serial} with Bosch server. Try to reconnect.."
            )

            # Reset values
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
            await asyncio.wait_for(self._event.wait(), timeout=9)
        except asyncio.TimeoutError:
            raise
        finally:
            self._request = ""
