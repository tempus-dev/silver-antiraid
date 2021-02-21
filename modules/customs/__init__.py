from .cmds import CustomCommands

def setup(bot):
    bot.add_cog(CustomCommands(bot))
