import logging
from typing import Optional

import discord
import discord.app_commands as commands
from discord.ext.commands import Bot, Cog

from core.utils import io


async def setup(bot):
    await bot.add_cog(Help(bot))

class Help(Cog):
    """Cog for the help command."""

    def __init__(self, bot: Bot):
        super().__init__()
        self.bot = bot
        self.log = logging.getLogger(__name__)

    @commands.command(name="help", description="A brief overview over my features.")
    async def help_command(self, interaction: discord.Interaction):
        embed = io.message(
            ":sparkles: Vibingway\n\n"
            "There isn't much to be said here just yet. Come back later.",
            thumbnail=self.bot.user.avatar.url,
            fields=[
                dict(name="Owner", value="Maxee#0001")
            ]
        )

        await interaction.response.send_message(embed=embed)