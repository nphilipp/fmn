import asyncio
import logging
import sys
import traceback

import backoff
from fastapi.concurrency import run_in_threadpool
from fedora_messaging import api
from fedora_messaging import exceptions as fm_exceptions
from fedora_messaging.message import Message

log = logging.getLogger(__name__)


def backoff_hdlr(details: dict) -> None:
    log.warning(f"Publishing message failed. Retrying. {traceback.format_tb(sys.exc_info()[2])}")


def giveup_hdlr(details: dict) -> None:
    log.error(f"Publishing message failed. Giving up. {traceback.format_tb(sys.exc_info()[2])}")


@backoff.on_exception(
    backoff.expo,
    (fm_exceptions.ConnectionException, fm_exceptions.PublishException),
    max_tries=3,
    on_backoff=backoff_hdlr,
    on_giveup=giveup_hdlr,
)
def _publish(message: Message) -> None:
    api.publish(message)


async def publish(message: Message) -> None:
    # Fire and forget
    asyncio.ensure_future(run_in_threadpool(_publish, message=message))
