import discord
import time
from discord.ext import commands
from pymongo import ReturnDocument

from .env import MAINTAINERS


class PermissionsManager:
    """
    Manages and allows the manipulation of guild permissions.

    Copied from [nyawesome](https://github.com/PiTheSnep/nyawesome).
    """

    def __init__(self, bot):
        self.logger = bot.logger
        self.bot = bot
        self.db = bot.db
        self.guild_cache = {}

    # GET METHODS
    async def get_guild_config(self, guild_id):
        """Fetch the permission config of the specified guild ID."""

        # Check if fresh document exists in the cache.
        cached_guild = self.get_cached_guild(guild_id)
        if cached_guild:
            return cached_guild

        conf = await self.db.guild_config.find_one({"_id": str(guild_id)}) or {}

        if conf.get("permissions"):
            self.cache_guild(guild_id, conf.get("permissions"))

        return conf.get("permissions") if conf and conf.get("permissions") else None

    def extract_permission(self, id_resolvable, field, permissions):
        """UTIL: Extract permission levels from db data."""

        if str(id_resolvable) in MAINTAINERS:
            return 100

        if permissions.get(field) and permissions.get(field).get(str(id_resolvable)):
            return permissions.get(field).get(str(id_resolvable))
        else:
            return 0

    async def get_member_permission(self, member: discord.Member):
        """Get the raw permission level of a member."""

        if str(member.id) in MAINTAINERS:
            return 100

        permissions = await self.get_guild_config(member.guild.id)
        perm_level = 99 if member.guild.owner.id == member.id else 0

        if permissions:
            for role in member.roles:
                curr_role_perm = self.extract_permission(
                    role.id, "roles", permissions)
                if curr_role_perm > perm_level:
                    perm_level = curr_role_perm

            pure = self.extract_permission(member.id, "members", permissions)
            return perm_level if perm_level > pure else pure
        else:
            return perm_level

    async def get_role_permission(self, role: discord.Role):
        """Get the raw permission level of a role."""

        permissions = await self.get_guild_config(role.guild.id)
        if permissions:
            return self.extract_permission(role.id, "roles", permissions)
        else:
            return 0

    async def get_permission(self, member_or_role):
        """UTIL: Get the raw permission level of either a role or a member."""

        if (isinstance(member_or_role, discord.Member)):
            return await self.get_member_permission(member_or_role)
        else:
            return await self.get_role_permission(member_or_role)

    async def has_permission(self, member: discord.Member, req: int):
        """Checks whether or not a member has the required perm level."""

        if str(member.id) in MAINTAINERS:
            return True

        perm_level = 99 if member.guild.owner.id == member.id else 0
        # Command should always be runnable if permission level is zero.
        # Also check using owner permission => max efficiency when running commands as owner.
        if (req == 0 or perm_level >= req):
            return True

        permissions = await self.get_guild_config(member.guild.id)

        if permissions:
            for role in member.roles:
                curr_role_perm = self.extract_permission(
                    role.id, "roles", permissions)

                if curr_role_perm >= req:
                    return True

            pure = self.extract_permission(member.id, "members", permissions)

            if perm_level > pure:
                pure = perm_level

            return pure >= req

        else:
            return perm_level >= req

    async def get_cmd_permission(self, cmd: commands.Command, guild: discord.Guild):
        """Get the raw permission level of a command."""

        permissions = await self.get_guild_config(guild.id)
        if permissions:
            return self.extract_permission(cmd.qualified_name, "cmds", permissions)
        else:
            return 0

    # SET METHODS
    async def set_db_perm_level(self, guild_id, field, id_resolvable, perm_level):
        """UTIL: DB function for updating permissions given guild IDs, role/member IDs, fields and perm_levels."""

        self.logger.debug(
            f"[db] {guild_id}:{id_resolvable} => {perm_level}, type={field}")

        conf = await self.db.guild_config.find_one_and_update(
            {"_id": str(guild_id)},
            {"$set": {
                f"permissions.{field}.{str(id_resolvable)}": perm_level}},
            upsert=True, return_document=ReturnDocument.AFTER
            # This or is hopefully redundant due to the upsert flag, but
            # I'm just being cautious.
        ) or {}

        if conf.get("permissions") and conf.get("permissions").get(field) and conf.get("permissions").get(field).get(str(id_resolvable)) is not None:
            if conf.get("permissions").get(field).get(str(id_resolvable)) == perm_level:
                # Cache the guild.
                self.cache_guild(guild_id, conf.get("permissions"))

                return True

        # Something went horribly wrong - delete cache entry to ensure consistency.
        self.bot.logger.warning(
            f'Permission level update for guild "{guild_id}" was unsuccessful.')
        self.bot.logger.warning(
            f'Attempt to set {field} "{id_resolvable}" to perm_level {perm_level} failed.')
        self.delete_cached_guild(guild_id)

        return False

    async def set_member_permission(self, member: discord.Member, perm_level: int):
        """Set the permission level of a member."""

        # Clamp perm_level here for redundancy.
        perm_level = max(0, min(99, perm_level))

        return await self.set_db_perm_level(member.guild.id, "members", member.id, perm_level)

    async def set_role_permission(self, role: discord.Role, perm_level: int):
        """Set the permission level of a member."""

        # Clamp perm_level here for redundancy.
        perm_level = max(0, min(99, perm_level))

        return await self.set_db_perm_level(role.guild.id, "roles", role.id, perm_level)

    async def set_permission(self, member_or_role, perm_level: int):
        """UTIL: Set the permission level of either a role or a member."""

        if (isinstance(member_or_role, discord.Member)):
            return await self.set_member_permission(member_or_role, perm_level)
        else:
            return await self.set_role_permission(member_or_role, perm_level)

    async def set_cmd_permission(self, cmd: commands.Command, guild: discord.Guild, perm_level: int):
        """Set the permission level of a command."""

        # Clamp perm_level here for redundancy.
        perm_level = max(0, min(99, perm_level))

        return await self.set_db_perm_level(guild.id, "cmds", cmd.qualified_name, perm_level)

    # WS METHODS

    async def handle_permission_update_request(self, guild_id, obj_id, level, is_role=False):
        guild = self.bot.get_guild(int(guild_id))

        if not guild:
            return self.bot.logger.debug(
                "[ws] Could not find requested guild.")

        target = None

        if is_role:
            target = guild.get_role(int(obj_id))
        else:
            target = guild.get_member(int(obj_id))

        if not target:
            return self.logger.debug(f"[ws] Could not find obj '{guild_id}:{obj_id}'")
        else:
            return await self.set_permission(target, level)

    # CACHE-ORIENTED METHODS
    def cache_guild(self, guild_id, data):
        """Sets a guild to the cache."""

        # Cache guild configuration - only set if update was successful.
        self.guild_cache[guild_id] = data
        # Round value so it's less impactful on memory.
        self.guild_cache[guild_id]["last_refreshed"] = round(
            time.time())

        self.bot.logger.debug(f'Cached permission data for guild "{guild_id}".')

    def get_cached_guild(self, guild_id):
        """Returns a cached guild or none."""

        if self.guild_cache.get(guild_id) and time.time() - self.guild_cache.get(guild_id).get("last_refreshed") < 600:
            self.logger.debug(
                f'Using cached permission data for guild "{guild_id}".')
            return self.guild_cache.get(guild_id)
        else:
            return None

    def delete_cached_guild(self, guild_id):
        """Removes a guild from the cache."""

        did_delete = True if self.guild_cache.pop(
            guild_id, None) is not None else False

        if did_delete:
            self.bot.logger.debug(
                f'Deleted cached permission data for guild "{guild_id}".')

        return did_delete
