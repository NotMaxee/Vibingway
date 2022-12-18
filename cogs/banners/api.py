import asyncio
import datetime
import logging
import random
from io import BytesIO
from typing import Optional

import aiohttp
import asyncpg
import discord
from discord.ext.commands import Bot

from core.errors import Failure, Warning
from core.utils import io

MAX_FILESIZE = 10 * 1024 * 1024

CONTENT_TYPES = ("image/png", "image/jpeg", "image/jpg", "image/gif")

UPSERT_BANNER_SETTINGS = """
INSERT INTO banner_settings (guild_id, {column})
VALUES ($1, $2)
ON CONFLICT (guild_id)
DO UPDATE SET {column}=$2;
"""

SELECT_BANNER_SETTINGS = """
SELECT {column} from banner_settings WHERE guild_id=$1;
"""


class BannerException(Failure):
    """Base exception for banner-related errors."""
    pass

class CannotDownloadImage(BannerException):
    """Exception raised when an image can not be downloaded."""
    pass

class ImageDoesNotExist(BannerException):
    """Exception raised when a download attempt returns HTTP status code 404."""

class BadImage(BannerException):
    """Exception raised when attempting to add a banner that isn't
    an accepted image file or whose file size is too large.
    """

class CannotSetBanner(BannerException):
    """Exception raised when the banner can not be set for some reason."""
    pass


class BannerAPI:
    """Database helper for the banner module.

    Parameters
    ----------
    bot: Vibingway
        The bot instance.
    """

    def __init__(self, bot: Bot):
        self.log = logging.getLogger(__name__)
        self.bot: Bot = bot
        self.tasks: list[asyncio.Task] = []

    @property
    def db(self) -> asyncpg.Pool:
        return self.bot.db

    # Helpers

    def cleanup(self):
        self.log.info(f"Cleaning up {len(self.tasks)} task(s).")
        for task in self.tasks:
            task.cancel()

    async def download_image(self, url: str) -> bytes:
        """Attempt to download an image from a URL.

        Parameters
        ----------
        url: str
            The image URL.

        Returns
        -------
        bytes
            A bytestream representing the image.

        Raises
        ------
        CannotDownloadImage
            Exception raised when the image could not be downloaded
            for whatever reason.
        BadImage
            Exception raised when the provided url does not point to
            an accepted image type or the image is too big.
        """

        # Get the content type and file size.
        type: str = None
        size: int = None
        try:
            # TODO: Add a timeout.
            response: aiohttp.ClientResponse
            async with self.bot.session.head(url=url) as response:
                type = response.headers.get("content-type")
                size = response.headers.get("content-length")

                if response.status == 404:
                    raise ImageDoesNotExist("The image has been deleted.")
        except ImageDoesNotExist as error:
            self.log.error(f"Unable to fetch image {url!r}!", exc_info=error)
            raise error
        except Exception as error:
            self.log.error(f"Unable to fetch image {url!r}!", exc_info=error)
            raise CannotDownloadImage(f"I could not download the image information.") from error

        if type is None or type.lower() not in CONTENT_TYPES:
            raise BadImage("Invalid file type. Server banners must be `png`, `jpg` or `gif` image files.")

        elif size is None or int(size) > MAX_FILESIZE:
            raise BadImage("The image is larger than `10MB`. Please choose a smaller image.")

        # Download the image.
        # TODO: Add a timeout.
        # TODO: Ensure we don't download more than 10 MB.
        try:
            async with self.bot.session.get(url=url) as response:
                return await response.read()
        except Exception as error:
            self.log.error(f"Unable to download image {url!r}!", exc_info=error)
            raise CannotDownloadImage("I could not download the image.") from error

    # API methods

    async def set_enabled(self, guild: discord.Guild, enabled: bool):
        query = UPSERT_BANNER_SETTINGS.format(column="enabled")
        await self.db.execute(query, guild.id, enabled)

    async def get_enabled(self, guild: discord.Guild) -> bool:
        query = SELECT_BANNER_SETTINGS.format(column="enabled")
        value = await self.db.fetchval(query, guild.id)
        return bool(value)

    async def set_interval(self, guild: discord.Guild, interval: int):
        query = UPSERT_BANNER_SETTINGS.format(column="interval")
        await self.db.execute(query, guild.id, interval)

    async def get_interval(self, guild: discord.Guild) -> int:
        query = SELECT_BANNER_SETTINGS.format(column="interval")
        value = await self.db.fetchval(query, guild.id)
        return value or 30

    async def update_last_change(self, guild: discord.Guild):
        query = UPSERT_BANNER_SETTINGS.format(column="last_change")
        query = query.replace("$2", "CURRENT_TIMESTAMP")
        await self.db.execute(query, guild.id)

    async def get_last_change(self, guild: discord.Guild) -> datetime.datetime:
        query = SELECT_BANNER_SETTINGS.format(column="last_change")
        return await self.db.fetchval(query, guild.id)

    # Banner methods

    async def add_banner(self, guild: discord.Guild, user: discord.User, url: str) -> bool:
        """Add a new banner.

        Parameters
        ----------
        guild: discord.Guild
            The guild to add the banner for.
        user: discord.User
            The user that added the banner.
        url: str
            The image URL.

        Returns
        -------
        bool
            :obj:`True` if the banner has been added, :obj:`False`
            if the same banner has already been added before.
        """
        query = """
        INSERT INTO banners (guild_id, user_id, url)
        VALUES ($1, $2, $3);"""

        try:
            await self.db.execute(query, guild.id, user.id, url)
            return True
        except asyncpg.UniqueViolationError:
            return False

    async def remove_banner(self, guild: discord.Guild, url: str):
        """Remove a banner.

        Parameters
        ----------
        guild: discord.Guild
            The guild to remove the banner from.
        url: str
            The banner URL.
        """
        query = """DELETE FROM banners WHERE guild_id=$1 AND url=$2;"""
        await self.db.execute(query, guild.id, url)

    async def get_banners(self, guild: discord.Guild) -> list[tuple[str, int]]:
        """Get a list of all banners."""
        query = "SELECT * FROM banners WHERE guild_id=$1 ORDER BY id ASC;"
        rows = await self.db.fetch(query, guild.id)
        return [(row["url"], row["user_id"]) for row in rows]

    async def set_banner(self, guild: discord.Guild, url: str, reason:str=None):
        """Try to set the banner for the given guild.

        Updates the `last_change` value for the guild.

        Parameters
        ----------
        guild: discord.Guild
            The guild to set the banner for.
        url: str
            The URL of the banner image.
        reason: Optional[str]
            An optional reason to show in the audit log.
        """
        try:
            data: bytes = await self.download_image(url)
        except ImageDoesNotExist as error:
            self.log.error(f"Deleting banner {url!r} due to HTTP 404.", exc_info=error)
            await self.remove_banner(guild, url)
            raise error
        
        try:
            await guild.edit(banner=data, reason=reason)
        except discord.Forbidden:
            raise Failure("I do not have the necessary permissions to change the banner.")

        await self.update_last_change(guild)

    # Automatic updating

    async def rotate_banners(self):
        """Perform the automatic banner rotation."""
        self.log.debug("Rotating banners.")
        # Only take guilds into account in which we have the "manage guild"
        # permission and who support setting the server banner.
        ids = [
            guild.id for guild in self.bot.guilds
            if guild.me.guild_permissions.manage_guild
            and "BANNER" in guild.features
        ]

        self.log.debug(f"Valid guild IDs: {ids}")

        # Fetch settings for guilds whose interval expired.
        query = """
        SELECT * FROM banner_settings 
        WHERE guild_id=ANY($1::bigint[])
        AND enabled
        AND CURRENT_TIMESTAMP - "interval" * interval '1 minute' > last_change;
        """
        rows = await self.db.fetch(query, ids)

        for row in rows:
            guild = self.bot.get_guild(row["guild_id"])
            if not guild:
                continue
            
            self.log.info(f"Creating banner update task for guild {guild.name!r}.")
            task = asyncio.create_task(self._show_random_banner(guild))
            task.add_done_callback(self._show_random_banner_callback)

    async def _show_random_banner(self, guild: discord.Guild):
        """Show a random banner for the given guild."""
        self.log.debug(f"Showing random banner for guild {guild.name!r}.")
        banners = await self.get_banners(guild)

        if len(banners) == 0:
            self.log.warn(f"Guild {guild.name!r} has no banners. Disabling automatic rotation.")
            await self.set_enabled(guild, False)
            return

        # Get a random banner and try to set it.
        url, _ = random.choice(banners)

        try:
            await self.set_banner(guild, url)
        except Exception as error:
            self.log.error(f"Unable to update banner for guild {guild.name!r}: {error}", exc_info=error)

    def _show_random_banner_callback(self, task: asyncio.Task):
        error = task.exception()
        if error:
            self.log.error("An error occured in a show banner task!", exc_info=error)

        try:
            self.tasks.remove(task)
        except ValueError:
            pass