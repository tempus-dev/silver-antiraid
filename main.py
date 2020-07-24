import asyncio
import discord

from struc import Silver
from utils.env import TOKEN


def main():
    bot = Silver(command_prefix="!")

    @bot.check
    async def command_permissions(ctx):
        if not isinstance(ctx.author, discord.Member):
            return True

        perm_level = await bot.permissions.get_cmd_permission(ctx.command, ctx.guild)
        if await bot.permissions.has_permission(ctx.author, perm_level):
            return True
        else:
            return False

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(bot.start(TOKEN))
    except KeyboardInterrupt:
        loop.run_until_complete(bot.logout())
    finally:
        loop.close


if __name__ == '__main__':
    main()
