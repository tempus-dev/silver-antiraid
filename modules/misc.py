import discord
from discord.ext import commands

from struc.commands import CustomCommand


class Misc(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db

    @commands.command(cls=CustomCommand)
    async def in_role(self, ctx, role_id):
        roles= ctx.guild.roles
        role = discord.utils.get(roles, id=int(role_id))
        await ctx.send("Role could not be found.") if not role else None
        for member in ctx.guild.members:
            if role in member.roles:
                await ctx.send(f"{member} ({member.id})")


def setup(bot):
    bot.add_cog(Misc(bot))
