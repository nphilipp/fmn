import logging
from typing import TYPE_CHECKING

from ..backends import FASJSONAsyncProxy, PagureAsyncProxy

if TYPE_CHECKING:
    from fedora_messaging.message import Message

    from ..core.config import Settings


log = logging.getLogger(__name__)


class Requester:
    def __init__(self, config: "Settings") -> None:
        self.distgit = PagureAsyncProxy(config.distgit_url)
        self.fasjson = FASJSONAsyncProxy(config.fasjson_url)

    async def invalidate_on_message(self, message: "Message") -> None:
        await self.distgit.invalidate_on_message(message)
        await self.fasjson.invalidate_on_message(message)
