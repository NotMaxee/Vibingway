from .cog import Banners

async def setup(bot):
    await bot.add_cog(Banners(bot))

async def teardown(bot):
    pass
