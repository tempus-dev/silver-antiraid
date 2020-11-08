from .sync import Sync

def setup(bot):
    bot.add_cog(Sync(bot))
