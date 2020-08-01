from discord.ext.commands import Command, Group


class CustomCommand(Command):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.perm_level = kwargs.get('perm_level', None)


class CustomGroup(Group):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.perm_level = kwargs.get('perm_level', None)
