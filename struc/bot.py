import logging
import os
import traceback

from discord.ext import commands

import motor.motor_asyncio as motor
from utils.env import DATABASE_URI, LOG_LEVEL
from utils.permissions import PermissionsManager


class Silver(commands.Bot):
    """
    Wrapper class for silver.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.logger = logging.getLogger("utils")
        self.logger.setLevel(int(LOG_LEVEL))

        sh = logging.StreamHandler()
        sh.setFormatter(logging.Formatter(
            '%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
        self.logger.addHandler(sh)

        self.logger.debug("Setting up database...")
        self.db = motor.AsyncIOMotorClient(DATABASE_URI).silver

        self.logger.debug("Setting up permissions...")
        self.permissions = PermissionsManager(self)

    async def on_ready(self):
        # Console write when bot starts
        self.logger.info(
            f'\n\nLogged in as: {self.user.name} - {self.user.id}\n')

        # load cogs
        cog_count = 0
        cogs = ["modules." + cog.replace(".py", "") for cog in os.listdir("./modules") if not cog.startswith('__')]
        self.logger.debug(f"Modules to load: {', '.join(cogs)}")

        for ext in cogs:
            try:
                self.logger.info(f"Loading {ext}...")
                self.load_extension(ext)
                cog_count += 1
            except Exception as e:
                error = "".join(traceback.format_exception(
                        type(e), e, e.__traceback__))
                self.logger.exception(f'Failed to load module {ext}.\n{error}')

        self.logger.debug(f"Successfully loaded {cog_count} modules.")

        self.logger.info("Initialization complete.")
        self.logger.info('------')
