import logging
from typing import Optional

import discord
import discord.app_commands as commands
from discord.ext.commands import Bot, Cog

from core.utils import io


class Banners(Cog):
    """Cog for banner commands."""

    def __init__(self, bot: Bot):
        super().__init__()

        # Internal setup.
        self.log = logging.getLogger(__name__)
        self.bot = bot

    # Command groups.

    banner = commands.Group(name="banner", description="Banner commands.", guild_only=True)

    # Banner commands.

    @banner.command(name="add", description="Add a new banner.")
    @commands.describe(url="URL of the banner image.")
    async def banner_add(self, interaction: discord.Interaction, url: str):
        # TODO: Check url and ensure it is an actual image.
        await interaction.response.send_message("This command is not quite ready yet.")
    
    @banner.command(name="remove", description="Remove a banner.")
    async def banner_remove(self, interaction: discord.Interaction):
        # TODO: Show a paginated dialog that lets the user remove banners.
        await interaction.response.send_message("This command is not quite ready yet.")
    
    @banner.command(name="list", description="View a list of all banners.")
    async def banner_list(self, interaction: discord.Interaction):
        # TODO: Show a paginated dialog of all banners.
        await interaction.response.send_message("This command is not quite ready yet.")
    
    @banner.command(name="change", description="Change the current banner.")
    async def banner_list(self, interaction: discord.Interaction):
        # TODO: Show a paginated dialog of all banners. let the user set one.
        await interaction.response.send_message("This command is not quite ready yet.")
    
    