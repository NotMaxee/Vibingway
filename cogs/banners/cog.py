import asyncio
import logging
from typing import Optional

import discord
import discord.app_commands as commands
from discord.ext.commands import Bot, Cog

from core.errors import Failure, Warning
from core.utils import io

from .api import BannerAPI
from .ui import BannerView


class Banners(Cog):
    """Cog for banner commands."""

    def __init__(self, bot: Bot):
        super().__init__()

        # Internal setup.
        self.log = logging.getLogger(__name__)
        self.bot = bot
        self.api = BannerAPI(self.bot)

        # Apply default permissions.
        decorate = commands.default_permissions(manage_guild=True)
        decorate(self.banner)

        # Need to manually set module as we are creating group objects directly
        # rather than creating a subclass for them. Otherwise reloading any
        # other extension produces an error.
        # See line 1588 in app_commands/commands.py.
        self.banner.module = self.__module__

        # Create the banner changing task.
        self._task = self.bot.loop.create_task(self._banner_rotation())
        self._task.add_done_callback(self._banner_rotation_callback)
    
    # Banner rotation task.

    async def _banner_rotation(self):
        await self.bot.wait_until_ready()
        
        # Task is cancelled when we shut things down, so this can run forever.
        interval: int = 300 # Check for banner changes every 5 minutes.
        self.log.info(f"Starting banner rotation task. Interval is {interval}s.")
        
        while not self.bot.is_closed():
            await self.api.rotate_banners()
            await asyncio.sleep(interval) 

        self.log.info("Banner rotation task stopped as the bot is closed.")

    def _banner_rotation_callback(self, task: asyncio.Task):
        # Handle errors that might occur while running the banner task.
        if task.cancelled():
            return

        error = task.exception()
        if error is None:
            return

        self.log.error("An error occured in the banner task!", exc_info=error)

        cog = self.bot.get_cog("Debug")
        if not cog:
            return

        self.bot.loop.create_task(cog.log_error(error))

    async def cog_unload(self):
        # Clean up the banner rotation task when unloading the cog.
        self.log.info("Cleaning up banner rotation task and API module.")
        self._task.cancel() 
        self.api.cleanup()

    # Helpers

    def check_can_set_banner(self, guild: discord.Guild):
        """Checks whether the given guild supports setting the banner
        and whether the bot has the manage_guild permission.
        
        Parameters
        ----------
        guild: discord.Guild
            The guild to check.
        
        Raises
        ------
        Failure
            Exception raised when the guild does not support setting the banner.
        """
        if not "BANNER" in guild.features:
            raise Failure("Banner rotation can not be enabled for this guild as it does not have a high enough boost level to support this feature.")

        if not guild.me.guild_permissions.manage_guild:
            raise Failure("I am missing the `manage guild` permission to change the server banner.")

    # Command groups.

    banner = commands.Group(name="banner", description="Banner commands.", guild_only=True)

    # Banner commands.

    @banner.command(name="add", description="Add a new banner. Maximum file size is 10MB.")
    @commands.describe(url="URL of the banner image. Must be a PNG, JPG or GIF.")
    async def banner_add(self, interaction: discord.Interaction, url: str):
        await interaction.response.defer(thinking=True)
        await self.api.download_image(url)
        success = await self.api.add_banner(interaction.guild, interaction.user, url)

        if not success:
            raise Failure("The image has already been added to the banner rotation.")
        
        # Send message.
        embed = io.success("The image has been added to the banner rotation.")
        embed.set_thumbnail(url=url)
        await interaction.followup.send(embed=embed)
    
    @banner.command(name="list", description="View a list of all banners and set / remove banners.")
    async def banner_list(self, interaction: discord.Interaction):
        view = await BannerView.create(interaction, self.api)
        await interaction.response.send_message(embed=view.get_embed(), view=view)
        await view.wait()
        
    @banner.command(name="toggle", description="Toggle automated banner changing.")
    @commands.choices(enabled=[
        commands.Choice(name="on", value=1),
        commands.Choice(name="off", value=0)
    ])
    async def banner_toggle(self, interaction: discord.Interaction, enabled:Optional[commands.Choice[int]]):
        if enabled is None:
            enabled = await self.api.get_enabled(interaction.guild)
            enabled = "on" if enabled else "off"
            embed = io.success(f"Automatic banner rotation is currently `{enabled}`.")
            await interaction.response.send_message(embed=embed)
            return

        # Check whether we can enable.
        previous = await self.api.get_enabled(interaction.guild)

        if previous == enabled.value:
            raise Failure(f"Automatic banner rotation is already `{enabled.name}`.")
        elif not previous and enabled.value:
            self.check_can_set_banner(interaction.guild)

        await self.api.set_enabled(interaction.guild, bool(enabled.value))
        embed = io.success(f"Automatic banner rotation is now `{enabled.name}`.")
        await interaction.response.send_message(embed=embed)
    
    @banner.command(name="interval", description="Set the banner change interval.")
    @commands.describe(interval="The delay inbetween banner changes in minutes.")
    async def banner_interval(self, interaction: discord.Interaction, interval: Optional[commands.Range[int, 5, None]]):
        if interval is not None:
            await self.api.set_interval(interaction.guild, interval)
            embed = io.success(f"Banner change interval set to `{interval}` minutes.")
            await interaction.response.send_message(embed=embed)
        else:
            interval = await self.api.get_interval(interaction.guild)
            embed = io.success(f"The banner interval is currently set to `{interval} minutes.")
            await interaction.response.send_message(embed=embed)

    