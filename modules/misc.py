import discord
import random
from discord.ext import commands
from struc.commands import CustomCommand


class Misc(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db
        self.hug_phrases = [
        "<@{a}> gave <@{b}> a big big hug!",
        "With a great big hug from <@{a}>\nand a gift from me to you\nWon't you say you love me too <@{b}>?",
        "<@{a}> dabbed on <@{b}> haters and gave them a hug.",
        "<@{b}> unexpectedly received a big hug from <@{a}>",
        "<@{a}> reached out their arms, wrapped them around <@{b}> and gave them a giant hug!"
    ]

    @commands.command(cls=CustomCommand)
    async def hug(self, ctx, person: discord.Member = None):
        """Hugs someone."""
        try:
            await ctx.message.delete()
        except:
            pass
        if not person:
            return await ctx.send("<@{a}> tried to hug nobody, but the **V O I D** was unable to do anything, and could only stare back in return.".format(
                    a=ctx.author.id))
        message = random.choice(self.hug_phrases)
        return await ctx.send(message.format(a=str(ctx.author.id), b=str(person.id)))

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
