from discord.ext import commands


class AntiRaid(commands.Cog, name="Antiraid"):

    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db
        self.guild_cache = {}

    async def get_guild_config(self, guild_id):
        """Fetch the antiraid config of the specified guild ID."""

        # Check if fresh document exists in the cache.
        cached_guild = self.get_cached_guild(guild_id)
        if cached_guild:
            return cached_guild

        conf = await self.db.guild_config.find_one({"_id": str(guild_id)}) or {}

        if conf.get("antiraid"):
            self.cache_guild(guild_id, conf.get("antiraid"))

    async def on_test_event(self, member):
        antiraid = await self.get_guild_config(member.guild.id)
        if not antiraid:
            return

        print('test_event')


def setup(bot):
    bot.add_cog(AntiRaid(bot))
