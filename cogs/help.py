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

    @commands.command(name="help", description="A compact overview of my features.")
    async def help_command(self, interaction: discord.Interaction):
        embed = io.message(
            ":sparkles: **Vibingway**\n\n"
            "Hey there, I'm Vibingway. I primarily do music commands and whatever other things my developer decides to burden me with. "
            "All of my commands are slash commands, so you can see a complete list of them by simply typing `/`.\n\n"
            "While you *can* invite me to your own server, please note that I am a private Discord bot. Don't invite me "
            "to any bigger Discord servers, or odds are I will be shut down. Also, quite frankly, I'd rather not up my workload even more...\n\n"
            "For questions and feature requests, please contact my developer `Maxee#0001`.\n",
            thumbnail=self.bot.user.avatar.url
        )

        await interaction.response.send_message(embed=embed)