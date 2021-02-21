from discord.ext import commands
from struc.commands import CustomCommand


# The check to ensure this is the guild used where the command was made
def guild_check(_custom_commands):
    async def predicate(ctx):
        return True # idrk if it *needs* to check that
    return commands.check(predicate)

class CustomCommands(commands.Cog):

    """ Each entry in _custom_commands will look like this:
    {
        guild_id1: {
            "command_name": {
                "name": "command_name",
                "content": "Output for command",
                "author": author_id,
                "whitelisted_users": [],
                "blacklisted_users": []
            }
        }
        "command_name": {
            guild_id: "This guild's output",
            guild_id2: "This other guild's output",
        }
    }
    """
    _custom_commands = {}

    @commands.command(cls=CustomCommand)
    async def add_command(self, ctx, name, *, output):
        # First check if there's a custom command with that name already
        guild_custom_commands = self._custom_commands.get(ctx.guild.id)
        if not guild_custom_commands:
            existing_command = False
        else:
            existing_command = guild_custom_commands.get(name)
        # Check if there's a built in command, we don't want to override that
        if existing_command is None and ctx.bot.get_command(name):
            return await ctx.send(f"A built in command with the name {name} is already registered")

        # Now, if the command already exists then we just need to add/override the message for this guild
        if existing_command:
            self._custom_commands[ctx.guild.id][name] = output
        # Otherwise, we need to create the command object
        else:
            @commands.command(cls=CustomCommand, name=name, help=f"Custom command: Outputs your custom provided output")
            @guild_check(self._custom_commands)
            async def cmd(self, ctx):
                await ctx.send(self._custom_commands[ctx.guild.id][ctx.invoked_with]['content'])

            cmd.cog = self
            # And add it to the cog and the bot
            self.__cog_commands__ = self.__cog_commands__ + (cmd,)
            ctx.bot.add_command(cmd)
            # Now add it to our list of custom commands
            if not guild_custom_commands:
                self._custom_commands[ctx.guild.id] = {}
            self._custom_commands[ctx.guild.id][name] = {"name": name, "content": output, "author": ctx.author.id, "whitelisted_users": [], "blacklisted_users": []}
        await ctx.send(f"Added a command called {name}")

    @commands.command(cls=CustomCommand)
    async def remove_command(self, ctx, name):
        # Make sure it's actually a custom command, to avoid removing a real command
        if name not in self._custom_commands or ctx.guild.id not in self._custom_commands[name]:
            return await ctx.send(f"There is no custom command called {name}")
        # All that technically has to be removed, is our guild from the dict for the command
        del self._custom_commands[name][ctx.guild.id]
        await ctx.send(f"Removed a command called {name}")

