from .cog import Owner
import discord.app_commands as commands

async def setup(bot):
    await bot.add_cog(Owner(bot))

async def teardown(bot):
    pass
