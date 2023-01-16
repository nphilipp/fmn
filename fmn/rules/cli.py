from pprint import pprint

import click

from ..core.config import get_settings
from ..database import init_sync_model, sync_session_maker
from .cache import cache
from .requester import Requester


@click.group("cache")
def cache_cmd() -> None:
    """Work with the cache in FMN."""


@cache_cmd.command("get-tracked")
def get_tracked() -> None:
    """Show the current tracked value."""
    cache.configure()
    init_sync_model()
    db = sync_session_maker()
    requester = Requester(get_settings().dict()["services"])
    pprint(cache.get_tracked(db, requester))


@cache_cmd.command("delete-tracked")
def delete_tracked() -> None:
    """Invalidate the current tracked value."""
    cache.configure()
    cache.invalidate_tracked()
    print("Tracked cache invalidated.")
