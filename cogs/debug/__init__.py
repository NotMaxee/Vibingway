from .cog import Debug

async def setup(bot):
    await bot.add_cog(Debug(bot))

async def teardown(bot):
    pass
