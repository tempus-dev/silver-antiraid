import asyncio
import traceback

import discord

from discord.ext import commands

from .user_db import Positions, Users
from struc.commands import CustomCommand, CustomGroup


class Sync(commands.Cog):
    """This does the syncing of roles across servers."""

    def __init__(self, bot):
        self.bot = bot
        self.quits = ['quit', 'exit', 'stop', 'cancel']
        self.yes = ['y', 'yes', 'ye', 'yea', 'ya', 'sure', 'mhm']
        self.positions = Positions(bot)
        self.users = Users(bot)
        self.event_was_triggered_by_join = {}
        self.role_added_on_join = {}

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        self.event_was_triggered_by_join[member.id] = True
        user = await self.users.syncable_user(member.id)
        if not user:
            return 
        print(user)
        for mg in user:
            user = await self.users.get_user(mg, str(member.id))
            pos = user['positions']
            for x in pos:
                v = await self.positions.get_position(mg, x)
                roles = v['roles'].get(str(member.guild.id))
                if not roles:
                    continue
                for r in roles:
                    print(f"member_join printing role {r}")
                    r_obj = discord.utils.get(member.guild.roles, id=int(r))
                    # TODO: log shit here
                    try:
                        await member.add_roles(r_obj, reason="Line 43")
                        self.role_added_on_join[member.id] = True
                        # TODO: Maybe have a more useful reason? lol
                    except Exception as e: # TODO: catch errors properly
                        print(e)
                        pass

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member) -> None:
        if before.roles == after.roles:
            return
        if self.event_was_triggered_by_join.get(before.id):
            self.event_was_triggered_by_join[before.id] = None
            return 

        user = await self.users.syncable_user(before.id)
        if not user:
            return

        if self.role_added_on_join.get(str(before.id)):
            self.role_added_on_join[before.id] = False
            return

        await self.other_member_update(before, after)

        for guild in user:
            user = await self.users.get_user(guild, before.id)
            pos = user['positions']
            for x in pos:
                pos_obj = await self.positions.get_position(guild, x)
                roles = pos_obj['roles'].get(str(before.guild.id))
                if not roles:
                    continue
                for r in roles:
                    r_obj1 = discord.utils.get(before.roles, id=int(r))
                    r_obj2 = discord.utils.get(after.roles, id=int(r))

                    if r_obj2:
                        continue

                    elif r_obj1 and not r_obj2:
                        # TODO: Log the inconsistency you're about to remedy
                        print("Inconsistency checker saw something")
                        await asyncio.sleep(10)
                        new_member = discord.utils.get(after.guild.members, id=after.id)
                        if r_obj1 not in new_member.roles:
                            await new_member.add_roles(r_obj1, reason="Line 86")
                            # TODO: log the role addition here

                    elif not r_obj1 and not r_obj2:
                        r_obj = discord.utils.get(after.guild.roles, id=int(r))
                        await before.add_roles(r_obj, reason="Line 91.")

    async def other_member_update(self, before: discord.Member, after: discord.Member) -> None:
        for role in after.roles:
            data = await self.positions.syncable_role(str(role.id))
            if not data:
                continue
            guilds = await self.users.syncable_user(after.id)
            if data['master_guild'] in guilds:
                user = await self.users.get_user(data['master_guild'], before.id)
                if data['position'] in user['positions']:
                    continue
                else:
                    await after.remove_roles(role, reason="line 105")
            else:
                await after.remove_roles(role, reason="line 107")
                # TODO: Log shiz

    @commands.command(cls=CustomCommand, perm_level=99)
    async def promote(self, ctx, member: discord.Member, pos: str) -> None:
        """This promotes someone."""
        uid = member.id
        tick = "<:sfs_tick:514531878993133584>"
        message = await ctx.send(f"Are you sure you want to promote {member.mention} ({member} {member.id}) to {pos}?"
                                 " If not, this message will expire in 15 seconds."
                                 f" Otherwise, click the {tick} to continue.")
        await message.add_reaction(tick)
        try:
            await ctx.bot.wait_for("reaction_add", 
                                   timeout=15, 
                                   check=lambda r,u: str(r.emoji) == tick \
                                       and u == ctx.author \
                                       and r.message.channel == ctx.channel
                                    )
        except asyncio.TimeoutError:
            await message.edit(content="Nevermind.")
            await message.remove_reaction(tick)
            return
        await message.delete()
        try:
            u = await self.users.add_user_pos(str(ctx.guild.id), uid, pos)
            if not u:
                return await ctx.send("That position does not exist.")
        except Exception as e:
            if ctx.author.id == 286246724270555136:
                error = "".join(traceback.format_exception(
                        type(e), e, e.__traceback__))
                await ctx.send("```py\n"+error+"\n```")
            else:
                await ctx.send("Woops. Looks like we errored.")
            return

        await ctx.send("Promotion successful!")

    @commands.group(cls=CustomGroup, perm_level=99)
    async def position(self, ctx) -> None:
        """Position editing commands!"""
        pass

    @position.command(cls=CustomCommand, perm_level=99)
    async def name(self, ctx, old_name: str, new_name: str) -> None:
        tick = "<:sfs_tick:514531878993133584>"
        message = await ctx.send("If you are not in the guild where everything should be synced from"
                                  " (The master guild), please execute this command there."
                                  f" Otherwise, click the {tick} to continue.")
        await message.add_reaction(tick)
        try:
            await ctx.bot.wait_for("reaction_add", 
                                   timeout=60, 
                                   check=lambda r,u: str(r.emoji) == tick \
                                       and u == ctx.author \
                                       and r.message.channel == ctx.channel
                                    )
        except asyncio.TimeoutError:
            await message.edit(content="Timed out.")
            await message.remove_reaction(tick)
            return
        await message.delete()
        try:
            await self.positions.update_position_name(ctx.guild.id, old_name, new_name)
        except ValueError as e:
            return await ctx.send(e)
        except Exception as e:
            if ctx.author.id == 286246724270555136:
                error = "".join(traceback.format_exception(
                        type(e), e, e.__traceback__))
                await ctx.send("```py\n"+error+"\n```")
            else:
                await ctx.send("Woops. Looks like we errored.")
            return

        await ctx.send("Successfully updated the position name.")


    @position.command(cls=CustomCommand, perm_level=99)
    async def hierarchy(self, ctx, pos_name: str, hierarchy: int) -> None:
        tick = "<:sfs_tick:514531878993133584>"
        message = await ctx.send("If you are not in the guild where everything should be synced from"
                                  " (The master guild), please execute this command there."
                                  f" Otherwise, click the {tick} to continue.")
        await message.add_reaction(tick)
        try:
            await ctx.bot.wait_for("reaction_add", 
                                   timeout=60, 
                                   check=lambda r,u: str(r.emoji) == tick \
                                       and u == ctx.author \
                                       and r.message.channel == ctx.channel
                                    )
        except asyncio.TimeoutError:
            await message.edit(content="Timed out.")
            await message.remove_reaction(tick)
            return
        await message.delete()
        try:
            await self.positions.update_position_hierarchy(ctx.guild.id, pos_name, hierarchy)
        except ValueError as e:
            return await ctx.send(e)
        except Exception as e:
            if ctx.author.id == 286246724270555136:
                error = "".join(traceback.format_exception(
                        type(e), e, e.__traceback__))
                await ctx.send("```py\n"+error+"\n```")
            else:
                await ctx.send("Woops. Looks like we errored.")
            return

        await ctx.send("Successfully updated the position hierarchy.")

    @position.command(cls=CustomCommand, perm_level=99)
    async def add_roles(self, ctx, pos_name: str, *, roles: str) -> None:
        tick = "<:sfs_tick:514531878993133584>"
        message = await ctx.send("If you are not in the guild where everything should be synced from"
                                  " (The master guild), please execute this command there."
                                  f" Otherwise, click the {tick} to continue.")
        await message.add_reaction(tick)
        try:
            await ctx.bot.wait_for("reaction_add", 
                                   timeout=60, 
                                   check=lambda r,u: str(r.emoji) == tick \
                                       and u == ctx.author \
                                       and r.message.channel == ctx.channel
                                    )
        except asyncio.TimeoutError:
            await message.edit(content="Timed out.")
            await message.remove_reaction(tick)
            return
        await message.delete()
        roles = roles.split(" ")
        if (len(roles) % 2) != 0:
            return await ctx.send("Please only provide ids in groups of two.")
        roles = [" ".join(roles[i:i+2]) for i in range(0, len(roles), 2)]
        role_dict = {}
        for role in roles:
            g_id = int(role.split(" ")[0])
            r_id = int(role.split(" ")[1])
            g_obj = discord.utils.get(ctx.bot.guilds, id=g_id)
            if not g_obj:
                await ctx.send(f"I'm either not in that server (`{g_id}`), or it doesn't exist.")
                return
            r_obj = discord.utils.get(g_obj.roles, id=r_id)
            if not r_obj:
                await ctx.send(f"I could not find the role (`{r_id}`).")
                return
            if not role_dict.get(str(g_id)):
                role_dict[str(g_id)] = []
            role_dict[str(g_id)].append(str(r_id))
        print(role_dict)
        try:
            await self.positions.add_position_roles(ctx.guild.id, pos_name, role_dict)
        except ValueError as e:
            return await ctx.send(e)
        except Exception as e:
            if ctx.author.id == 286246724270555136:
                error = "".join(traceback.format_exception(
                        type(e), e, e.__traceback__))
                await ctx.send("```py\n"+error+"\n```")
            else:
                await ctx.send("Woops. Looks like we errored.")
            return
        
        await ctx.send(f"Successfully updated the roles of {pos_name}!")


    @commands.group(cls=CustomGroup)
    async def create(self, ctx) -> None:
        """Commands for creating stuff."""
        pass

    @commands.group(cls=CustomGroup)
    async def qcreate(self, ctx) -> None:
        """Quick create commands without the interactive setup."""
        pass

    @qcreate.command(cls=CustomCommand, name='position', perm_level=99)
    async def pos_create(self, ctx, name: str, hierarchy: int, *, roles: str) -> dict:
        """This creates a position, but quicker."""
        tick = "<:sfs_tick:514531878993133584>"
        roles = roles.split(" ")
        if (len(roles) % 2) != 0:
            return await ctx.send("Please only provide ids in groups of two.")
        roles = [" ".join(roles[i:i+2]) for i in range(0, len(roles), 2)]
        role_dict = {}
        message = await ctx.send("If you are not in the guild where everything should be synced from"
                                  " (The master guild), please execute this command there."
                                  f" Otherwise, click the {tick} to continue.")
        await message.add_reaction(tick)
        try:
            await ctx.bot.wait_for("reaction_add", 
                                   timeout=60, 
                                   check=lambda r,u: str(r.emoji) == tick \
                                       and u == ctx.author \
                                       and r.message.channel == ctx.channel
                                    )
        except asyncio.TimeoutError:
            await message.edit(content="Timed out.")
            await message.remove_reaction(tick)
            return
        await message.delete()
        exists = await self.positions.get_position(ctx.guild.id, name)
        if exists:
            return await ctx.send("That position name is taken.")
        guilds = []
        for role in roles:
            g_id = int(role.split(" ")[0])
            r_id = int(role.split(" ")[1])
            g_obj = discord.utils.get(ctx.bot.guilds, id=g_id)
            if not g_obj:
                await ctx.send(f"I'm either not in that server (`{g_id}`), or it doesn't exist.")
                return
            r_obj = discord.utils.get(g_obj.roles, id=r_id)
            if not r_obj:
                await ctx.send(f"I could not find the role (`{r_id}`).")
                return
            if not role_dict.get(str(g_id)):
                role_dict[str(g_id)] = []
            role_dict[str(g_id)].append(str(r_id))
            guilds.append(g_id)
        try:
            await self.positions.create_position(ctx.guild.id, 
                                                       name, 
                                                       hierarchy, 
                                                       role_dict, 
                                                       guilds)
        except Exception as e:
            if ctx.author.id == 286246724270555136:
                error = "".join(traceback.format_exception(
                        type(e), e, e.__traceback__))
                await ctx.send("```py\n"+error+"\n```")
            else:
                await ctx.send("Woops. Looks like we errored.")
        await ctx.send(f"Great success! The position {name} was created.")

    @create.command(cls=CustomCommand, perm_level=99, name='position')
    async def _position(self, ctx) -> None:
        """This creates a position to sync."""
        msgs = [ctx.message]
        msgs.append(await ctx.send("Welcome to the interactive setup for syncing roles! "
                       "If you are not in the guild where everything should be synced from"
                       " (The master guild), please execute this command there."
                       " Otherwise, send `Y` to continue.\n"
                       "You can say `quit` to quit at any time."))
        def check(m):
            return m.channel == ctx.channel and m.author == ctx.author
        res1 = await ctx.bot.wait_for('message', check=check)
        msgs.append(res1)
        if res1.content.lower() not in self.yes:
            msgs.append(await ctx.send("Quitting..."))
            [await x.delete() for x in msgs]
            return
        msgs.append(await ctx.send("Alright, let's get started!\n"
                                    "You can type `quit` to quit at anytime.\n\n"
                                    "`Please enter the name of the position.`"))
        res2 = await ctx.bot.wait_for('message', check=check)
        if res2.content.lower() in self.quits:
            msgs.append(await ctx.send("Quitting..."))
            [await x.delete() for x in msgs]
            return
        msgs.append(res2)
        pos_name = res2.content
        exists = await self.positions.get_position(ctx.guild.id, pos_name)
        while exists:
            msgs.append(await ctx.send("Syncing to this position already exists!"
                                       " You can use {WIP} to update position information."
                                       "\n\nIf you wanted to update the position you named, "
                                       "respond with quit and use the commands mentioned. "
                                       "Otherwise, respond with another position name."))
            # TODO: Replace {WIP} with actual commands.
            res2 = await ctx.bot.wait_for('message', check=check)
            msgs.append(res2)
            pos_name = res2.content
            exists = await self.positions.get_position(ctx.guild.id, pos_name)
            # NOTE: doesnt acc listen for quit
        msgs.append(await ctx.send(f"Awesome! The name of the position is `{pos_name}`.\n"
                                   "Is this correct? (yes/no)"))
        res3 = await ctx.bot.wait_for('message', check=check)
        if res3.content.lower() in self.quits:
            msgs.append(await ctx.send("Quitting..."))
            [await x.delete() for x in msgs]
            return
        msgs.append(res3)
        incorrect = True
        if res3.content.lower() in self.yes:
            incorrect = False
        while incorrect:
            msgs.append(await ctx.send("Alright, please send the name of the position again."))
            res2 = await ctx.bot.wait_for('message', check=check)
            if res2.content.lower() in self.quits:
                msgs.append(await ctx.send("Quitting..."))
                [await x.delete() for x in msgs]
                return
            msgs.append(res2)
            pos_name = res2.content
            msgs.append(await ctx.send(f"Awesome! The name of the position is `{pos_name}`.\n"
                                       "Is this correct? (yes/no"))
            res3 = await ctx.bot.wait_for('message', check=check)
            if res3.content.lower() in self.quits:
                msgs.append(await ctx.send("Quitting..."))
                [await x.delete() for x in msgs]
                return
            if res3.content.lower() in self.yes:
                incorrect = False
                break
        msgs.append(await ctx.send("Sweet! Now, I'd like to know where this "
                                    "position falls in terms of hierarchy. "
                                    "Simply put, 0 is the highest (e.g owner) "
                                    "and you can go as low as you want with "
                                    "hierarchy (which would be a higher number.) "
                                    "Bit confusing, but hopefully that made sense!\n\n"
                                    "Please respond to this message with a hierachial value."))
        res4 = await ctx.bot.wait_for('message', check=check)
        msgs.append(res4)
        if res4.content.lower() in self.quits:
            msgs.append(await ctx.send("Quitting..."))
            [await x.delete() for x in msgs]
            return
        try:
            hierarchy = int(res4.content)
            is_int = True
        except ValueError:
            is_int = False
        while not is_int:
            msgs.append(await ctx.send("The hierarchical value has to be just a number."
                           " Check my previous message explaining it!"))
            res4 = await ctx.bot.wait_for('message', check=check)
            msgs.append(res4)
            if res4.content.lower() in self.quits:
                msgs.append(await ctx.send("Quitting..."))
                [await x.delete() for x in msgs]
                return
            try:
                hierarchy = int(res4.content)
                is_int = True
                break
            except ValueError:
                is_int = False
        # TODO: check this pl0x for "guild_id role_id" making sure wording is consistent
        msgs.append(await ctx.send("Wonderful! Now, I would like the roles this"
                                   " position should be syncing. \nFirst, **ensur"
                                   f"e I ({ctx.bot.user.name}) am *in* the guil"
                                   "d you provide.** Feel free to grab your ans"
                                   "wers and say 'quit' to stop quit and add me"
                                   " to the guild.\nEnsure I have the MANAGE R"
                                   "OLES permission as well, and am above the r"
                                   "ole you are setting to sync.\n\nPlease respond"
                                   " to this message with the guild id and the role id."
                                   " Here's an example: 123456789012345678 123456789012345678"))
        res5 = await ctx.bot.wait_for('message', check=check)
        if res5.content.lower() in self.quits:
            msgs.append(await ctx.send("Quitting..."))
            [await x.delete() for x in msgs]
            return
        msgs.append(res5)
        if res5.content.startswith('`'):
            res5.content = res5.content.replace('`', "")

        ids = res5.content.split(' ')
        is_two = len(ids) == 2
        if is_two:
            try:
                g_id = int(ids[0])
                r_id = int(ids[1])
                is_int = True
                g_obj = discord.utils.get(ctx.bot.guilds, id=g_id)
                if g_obj:
                    g_exists = True
                    r_obj = discord.utils.get(g_obj.roles, id=r_id)
                    r_exists = r_obj != None
                else:
                    g_exists = False
                    r_exists = False
            except ValueError:
                is_int = False
        overall = is_two and is_int and g_exists and r_exists

        while not overall:
            two_failed = "It looks like you got the formatting for the ID wrong! "
            two_failed += "The format is `guild_id role_id`. Please refer to the"
            two_failed += " original message for more information."

            int_failed = "It looks like you didn't put a proper ID!"
            int_failed += " Please input an actual ID, using the format"
            int_failed += " `guild_id role_id`."

            g_failed = "I couldn't find the guild provided. Please make"
            g_failed += " sure that I am in the guild and that the ID is"
            g_failed += " correct."

            r_failed = "I couldn't find that role within the guild provided."
            r_failed += " Please make sure that you have the right guild, and"
            r_failed += " that the role exists within the guild."
            cta = "\n\nPlease respond to this message with the guild id and the role id."
            cta += " Here's an example: 123456789012345678 123456789012345678"
            if not is_two:
                done = two_failed + cta
            elif not is_int:
                done = int_failed + cta
            elif not g_exists:
                done = g_failed + cta
            elif not r_exists:
                done = r_failed + cta
            else:
                done = "I don't have an error message. How did you get here? "
                done += "Something in the coding must've gone wrong. "
                done += "You can try again, if you'd like. Say quit at anytime to cancel."
                done += cta
            msgs.append(await ctx.send(done))

            res5 = await ctx.bot.wait_for('message', check=check)
            if res5.content.lower() in self.quits:
                msgs.append(await ctx.send("Quitting..."))
                [await x.delete() for x in msgs]
                return
            msgs.append(res5)
            ids = res5.content.split(' ')
            if res5.content.startswith('`'):
                res5.content = res5.content.replace('`', "")

            ids = res5.content.split(' ')
            is_two = len(ids) == 2
            if is_two:
                try:
                    g_id = int(ids[0])
                    r_id = int(ids[1])
                    is_int = True
                    g_obj = discord.utils.get(ctx.bot.guilds, id=g_id)
                    if g_obj:
                        g_exists = True
                        r_obj = discord.utils.get(g_obj.roles, id=r_id)
                        r_exists = r_obj != None
                    else:
                        g_exists = False
                        r_exists = False
                except ValueError:
                    is_int = False
            overall = is_two and is_int and g_exists and r_exists
        
        role_dict = {str(g_id): [str(r_id)]}
        try:
            pos = await self.positions.create_position(ctx.guild.id, 
                                                 pos_name, 
                                                 hierarchy, 
                                                 role_dict, 
                                                 [g_id])
        except Exception as e:
            await ctx.send("Woops. You've entered uncharted territory here."
                           " Send my regards to the chief. (The bot broke =p)\n\n"
                           f"Error: `Exception: {e}``")
            # TODO: ENsure we never get here
            # but if we do, log shiz.
            return

        await ctx.send("Great success! The position was created."
                       "\nIn the future, please use the associated" 
                       " quick command for a much quicker setup time!"
                        " The command for what you did here would look like: `"
                        f"{ctx.prefix}qcreate position {res2.content} {res4.content} {res5.content}`"
                        "You can also use qcreate position to add more "
                        "than one role at a time!")

        return pos
    # DEAAAAAAAAAAAAAAAAAAAAAAR GOD
    # CODING THIS WAS SO HARD
    # FUUCK I CANNOT BELIEVE I GOIT THROUGH IT ATALL
    # DEAAAAAR GOD

    