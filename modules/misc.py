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
        self.fight_phrases = [
        "<@{a}> fought with <@{b}> with a large fish.",
        "<@{a}> tried to fight <@{b}>, but it wasn't very effective!",
        "<@{a}> fought <@{b}>, but they missed.",
        "<@{a}> fought <@{b}> with a piece of toast.",
        "<@{a}> and <@{b}> are fighting with a pillow.",
        "<@{a}> aimed but missed <@{b}> by an inch.",
        "<@{b}> got duck slapped by <@{a}>",
        "<@{a}> tried to dab on <@{b}> but they tripped, fell over, and now they need @ someone",
        "<@{b}> was saved from <@{a}> by wumpus' energy!",
        "Dabbit dabbed on <@{b}> from a request by <@{a}>!",
        "Jet banned <@{a}> for picking a fight with <@{b}>!",
        "<@{a}> joined the game.\n<@{a}>: That's not very cash money of you.\n<@{b}>: What\nCONSOLE: <@{b}> was banned by an operator.\n<@{b}> left the game.",
        "<@{b}> tied <@{a}>’s shoelaces together, causing them to fall over.",
        "You are the Chosen One <@{a}>. You have brought balance to this world. Stay on this path, and you will do it again for the galaxy. But beware your heart said master <@{b}>",
        "<@{a}> used 'chat flood'. It wasn't very effective, so <@{b}> muted them."
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
    async def fight(self, ctx, person: discord.Member = None):
        """Fights someone."""
        try:
            await ctx.message.delete()
        except:
            pass
        if not person:
            return await ctx.send("<@{a}> tried to fight nobody, but the **V O I D** is unfightable, and could only stare back in return.".format(
                    a=ctx.author.id))
        message = random.choice(self.fight_phrases)
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
