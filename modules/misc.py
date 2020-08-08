import discord
from discord.ext import commands

from struc.commands import CustomCommand


class Misc(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db

    @commands.command(perm_level=100, cls=CustomCommand)
    async def announce(self, ctx, announcement: str, channel: discord.TextChannel) -> None:
        await channel.send(announcement)

    @commands.command(perm_level=100, cls=CustomCommand)
    async def audere(self, ctx):
        gif = discord.Embed(colour=discord.Color(0xb80c0c))
        gif.set_image(url="https://cdn.discordapp.com/attachments/520421468086075395/739254925338607636/audereverifygif.gif")
        await ctx.send(embed=gif)
        rules = discord.Embed(description="""__**𝘄𝗲𝗹𝗰𝗼𝗺𝗲**__

`🍒` rules !
〜no threats of raiding, doxing, leaking info, etc
〜no cp, gore, nsfw related content in #chat
〜no adv in serv or in dm, spamming, copying the server
〜don't beg for roles / promotions
〜use the right channels and keep chat english only!
〜follow discord tos """, color=discord.Color(0x090909))
        await ctx.send(embed=rules)
        info = discord.Embed(description="""**𝘄𝗲𝗹𝗰𝗼𝗺𝗲**

`🍒`booster perks !
1 boost
〜custom role + hex
〜pic perms
〜one server promotion with @.here ping

2 boosts
〜separate custom role + hex
〜higher chance of becoming staff
〜1 promo with @.everyone ping
〜 all the above""", color=discord.Color(0x090909))
        await ctx.send(embed=info)
        verify = discord.Embed(description="""`🍒` verify !

〜react to see the rest of 𝒂𝒖𝒅𝒆𝒓𝒆!! """)
        message = await ctx.send(embed=verify)

        await self.db.guild_config.find_one_and_update(
            {"_id": str(ctx.guild.id)},
            {"$set": {
                "misc.verification_message": str(message.id)
            }}
        )
        print(message.id)

    @commands.command(cls=CustomCommand, perm_level=99)
    async def jc_blacklist(self, ctx, member: discord.Member, reason: str) -> None:
        """This blacklists someone from the jazz club."""
        jc = discord.utils.get(ctx.guild.channels, id=741714741680013392)
        overwrites = {
            member: discord.PermissionOverwrite(read_messages=False)
        }

        await jc.edit(overwrites=overwrites, reason=reason)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if before.guild.id != 360462032811851777:
            return
        if before.roles == after.roles:
            return
        level = discord.utils.get(after.guild.roles, id=384281326456406019)
        if level in before.roles:
            return

        if level in after.roles:
            channel = discord.utils.get(after.guild.channels, id=741714741680013392)
            embed = discord.Embed(colour=after.color, description=f"Welcome {after.mention} to the Jazz Club! Everyone welcome them <3")
            await channel.send(embed=embed)


def setup(bot):
    bot.add_cog(Misc(bot))
