import time
import secrets

from discord.ext import commands
from pymongo import ReturnDocument

class PositionDoesNotExist(ValueError):
    pass

class PositionExists(ValueError):
    pass

class HierarchyFilled(ValueError):
    pass

class UserNotFound(ValueError):
    pass

class RoleExists(ValueError):
    pass

# TODO: Do all of this but like, efficiently.
# Way too much repeated code here. 

class Positions:
    """This manages the positions within the database."""

    def __init__(self, bot):
        self.logger = bot.logger
        self.bot = bot
        self.db = bot.db
        self._guild_cache = {}

    async def _get_guild_config(self, guild_id: str) -> dict:
        """Fetch the position config of the specified guild ID."""

        # Check if fresh document exists in the cache.
        cached_guild = self._get_cached_guild(guild_id)
        if cached_guild:
            return cached_guild

        conf = await self.db.guild_config.find_one({"_id": str(guild_id)}) or {}

        if conf.get("positions"):
            self._cache_guild(guild_id, conf.get("positions"))

        return conf.get("positions") if conf and conf.get("positions") else None

    # CACHE-ORIENTED METHODS
    def _cache_guild(self, guild_id, data):
        """Sets a guild to the cache."""

        # Cache guild configuration - only set if update was successful.
        self._guild_cache[guild_id] = data
        # Round value so it's less impactful on memory.
        self._guild_cache[guild_id]["last_refreshed"] = round(
            time.time())

        self.bot.logger.debug(f'Cached position data for guild "{guild_id}".')

    def _get_cached_guild(self, guild_id):
        """Returns a cached guild or none."""

        if self._guild_cache.get(guild_id) and time.time() - self._guild_cache.get(guild_id).get("last_refreshed") < 600:
            self.logger.debug(
                f'Using cached position data for guild "{guild_id}".')
            return self._guild_cache.get(guild_id)
        else:
            return None

    def _delete_cached_guild(self, guild_id):
        """Removes a guild from the cache."""

        did_delete = True if self._guild_cache.pop(
            guild_id, {}) is not None else False

        if did_delete:
            self.bot.logger.debug(
                f'Deleted cached position data for guild "{guild_id}".')

        return did_delete

    async def set_syncable_role(self, master_guild_id: str, guild_id: str, role_id: str, position: str) -> None:
        guild_id = str(guild_id)
        role = await self.db.syncable.find_one({"_id": str(role_id)}) or None
        if role:
            raise RoleExists("The role passed is already in a different position.") 
            # Why....would the role exist anyway ?
        if not position.startswith("pos_"):
            position = "pos_" + position
        await self.db.syncable.find_one_and_update(
            {"_id": str(role_id)},
            {"$set": {
                "master_guild": str(master_guild_id),
                "guild": str(guild_id),
                "position": position
            }},
            upsert=True, return_document=ReturnDocument.AFTER
        )
    
    # TODO: Cache shit. Fetching DB every time someone's role updates is inefficient.
    async def syncable_role(self, role_id: str) -> int:
        role = await self.db.syncable.find_one({"_id": str(role_id)}) or {}
        return role

    async def create_position(self, guild_id: str, name: str, hierarchy: int, roles: dict, guilds: list) -> str:
        """This adds a staff position to the database.

        A position is a staff member's title, we 
        use this information to sync to roles.
        """
        guild_id = str(guild_id)
        conf = await self.db.guild_config.find_one({"_id": str(guild_id)}) or {}
        # uuid = "pos_" + secrets.token_hex(6)
        if (await self.get_position(guild_id, name)):
            raise PositionExists("That position name is already in use.")



        pos = {"name": name, "hierarchy": hierarchy, "roles": roles, "watchlist": guilds}
        await self.db.guild_config.find_one_and_update(
            {"_id": str(guild_id)},
            {"$set": {
                f"positions.pos_{name}": pos}},
            upsert=True, return_document=ReturnDocument.AFTER
            # This or is hopefully redundant due to the upsert flag, but
            # I'm just being cautious.
        ) or {}

        for g, role in roles.items():
            for r in role:
                await self.set_syncable_role(guild_id, g, r, name)
        conf = await self.db.guild_config.find_one({"_id": str(guild_id)}) or {}
        self._cache_guild(guild_id, conf.get("positions"))
# TODO: yep. definitely need a specific function for writing things so I can cache.
        return True

    async def get_position(self, guild_id: str, name: str) -> dict:
        """This fetches a specific position from the database."""
        guild_id = str(guild_id)
        positions = await self._get_guild_config(guild_id)
        if positions:
            return positions.get("pos_" + name) if not name.startswith("pos_") else positions.get(name)

        else:
            return None

    async def get_all_positions(self, guild_id: str) -> list:
        """This fetches every position registered for a given guild."""
        guild_id = str(guild_id)
        conf = await self._get_guild_config(guild_id)
        positions = []
        for pos in conf:
            if not pos.startswith("pos_"):
                continue
            positions.append(conf[pos])

        return positions

    # TODO: Inefficient asf
    async def get_all_position_roles(self, guild_id: str) -> list:
        """This fetches every role for every position in every guild."""
        guild_id = str(guild_id)
        guilds = await self.db.guild_config.find({})
        roles = {}
        for guild in guilds:
            if not guild.get('positions'):
                continue
            guild_id = guild.get("_id")
            all_pos = await self.get_all_positions(guild_id)
            for pos in all_pos:
                roles[pos['name']] = pos['roles']
        return roles 
    
    async def update_position_watchlist(self, guild_id: str, name: str, guilds: list) -> dict:
        """This updates the list of guilds watched and updated."""
        guild_id = str(guild_id)
        conf = await self.db.guild_config.find_one({"_id": str(guild_id)}) or {}
        pos = await self.get_position(guild_id, name)
        if not pos:
            raise PositionDoesNotExist("That position could not be found.")

        pos['watchlist'] = pos['watchlist'] + guilds
        result = await self.db.guild_config.find_one_and_update(
            {"_id": str(guild_id)},
            {"$set": {
                f"positions.pos_{name}": pos}},
            upsert=True, return_document=ReturnDocument.AFTER
            # This or is hopefully redundant due to the upsert flag, but
            # I'm just being cautious
        ) or {}
        self._cache_guild(guild_id, conf.get("positions"))

        return result

    async def update_position_name(self, guild_id: str, name: str, new: str) -> dict:
        """This updates the name of a staff position in the database."""
        guild_id = str(guild_id)
        conf = await self.db.guild_config.find_one({"_id": str(guild_id)}) or {}
        pos = await self.get_position(guild_id, name)
        if not pos:
            raise PositionDoesNotExist("That position could not be found.")

        if (await self.get_position(guild_id, new)):
            raise PositionExists("That position name is already in use.")

        pos['name'] = new
        result = await self.db.guild_config.find_one_and_update(
            {"_id": str(guild_id)},
            {"$set": {
                f"positions.pos_{name}": pos}},
            upsert=True, return_document=ReturnDocument.AFTER
            # This or is hopefully redundant due to the upsert flag, but
            # I'm just being cautious.
        ) or {}
        self._cache_guild(guild_id, conf.get("positions"))

        return result

    async def update_position_hierarchy(self, guild_id: str, name: str, new: int) -> dict:
        """This updates the hierarchy of a staff position in the database."""
        guild_id = str(guild_id)
        conf = await self.db.guild_config.find_one({"_id": str(guild_id)}) or {}
        pos = await self.get_position(guild_id, name)
        if not pos:
            raise PositionDoesNotExist("That position could not be found.")

        all_pos = await self.get_all_positions(guild_id)
        for position in all_pos:
            if position['hierarchy'] == new and new != 0:
                raise HierarchyFilled("There is already a position at this hierarchy level.")

        pos['hierarchy'] = new
        result = await self.db.guild_config.find_one_and_update(
            {"_id": str(guild_id)},
            {"$set": {
                f"positions.pos_{name}": pos}},
            upsert=True, return_document=ReturnDocument.AFTER
            # This or is hopefully redundant due to the upsert flag, but
            # I'm just being cautious.
        ) or {}
        self._cache_guild(guild_id, conf.get("positions"))

        return result

    async def add_position_roles(self, guild_id: str, name: str,  roles: dict) -> dict:
        """This adds a role to a position."""
        guild_id = str(guild_id)
        conf = await self.db.guild_config.find_one({"_id": str(guild_id)}) or {}
        pos = await self.get_position(guild_id, name)
        if not pos:
            raise PositionDoesNotExist("That position could not be found.")
        for g_id, r_list in roles.items():
            if pos['roles'].get(g_id):
                for r_id in r_list:
                    pos['roles'][g_id].append(r_id)
            else:
                pos['roles'][g_id] = r_list

        result = await self.db.guild_config.find_one_and_update(
            {"_id": str(guild_id)},
            {"$set": {
                f"positions.pos_{name}": pos}},
            upsert=True, return_document=ReturnDocument.AFTER
            # This or is hopefully redundant due to the upsert flag, but
            # I'm just being cautious
        ) or {}
        for guild, role in roles.items():
            if not guild in pos['watchlist']:
                await self.update_position_watchlist(guild_id, name, [guild])
            for r in role:
                await self.set_syncable_role(guild_id, guild, r, name)

        self._cache_guild(guild_id, conf.get("positions"))

        return result


    async def remove_position_roles(self, guild_id: str, name: str, roles: dict) -> dict:
        """This removes a role from a given position."""
        guild_id = str(guild_id)
        conf = await self.db.guild_config.find_one({"_id": str(guild_id)}) or {}
        pos = await self.get_position(guild_id, name)
        if not pos:
            raise PositionDoesNotExist("That position could not be found.")

        for g in roles:
            pos['roles'].pop(g, None)

        result = await self.db.guild_config.find_one_and_update(
            {"_id": str(guild_id)},
            {"$set": {
                f"positions.pos_{name}": pos}},
            upsert=True, return_document=ReturnDocument.AFTER
            # This or is hopefully redundant due to the upsert flag, but
            # I'm just being cautious
        ) or {}
        for g, role in roles.items():
            for r in role:
                await self.db.syncable.find_one_and_delete({"_id": (str(r))})

        self._cache_guild(guild_id, conf.get("positions"))

        return result

    async def delete_position(self, guild_id: str, name: str) -> dict:
        """This deletes a staff position in the database."""
        guild_id = str(guild_id)
        conf = await self.db.guild_config.find_one({"_id": str(guild_id)}) or {}
        pos = await self.get_position(guild_id, name)
        if not pos:
            raise PositionDoesNotExist("That position could not be found.")
        for role in pos['roles']:
            r = role[list(role.keys())[0]]
            await self.db.syncable.find_one_and_delete({"_id": (str(r))})
        result = await self.db.guild_config.find_one_and_replace(
            {f"pos_{name}": pos},
            {},
            upsert=True, return_document=ReturnDocument.AFTER
            # This or is hopefully redundant due to the upsert flag, but
            # I'm just being cautious
        ) or {}
        self._cache_guild(guild_id, conf.get("positions"))

        return result

class Users:
    """This manages users within the database."""

    def __init__(self, bot):
        self.logger = bot.logger
        self.bot = bot
        self.db = bot.db
        self._guild_cache = {}

    async def _get_guild_config(self, guild_id: str) -> dict:
        """Fetch the user config of the specified guild ID."""

        # Check if fresh document exists in the cache.
        cached_guild = self._get_cached_guild(guild_id)
        if cached_guild:
            return cached_guild

        conf = await self.db.guild_config.find_one({"_id": str(guild_id)}) or {}

        if conf.get("users"):
            self._cache_guild(guild_id, conf.get("users"))

        return conf.get("users") if conf and conf.get("users") else None

    # CACHE-ORIENTED METHODS
    def _cache_guild(self, guild_id, data):
        """Sets a guild to the cache."""

        # Cache guild configuration - only set if update was successful.
        self._guild_cache[guild_id] = data
        # Round value so it's less impactful on memory.
        self._guild_cache[guild_id]["last_refreshed"] = round(time.time())

        self.bot.logger.debug(f'Cached user data for guild "{guild_id}".')

    def _get_cached_guild(self, guild_id):
        """Returns a cached guild or none."""

        if self._guild_cache.get(guild_id) and time.time() - self._guild_cache.get(guild_id).get("last_refreshed") < 600:
            self.logger.debug(
                f'Using cached user data for guild "{guild_id}".')
            return self._guild_cache.get(guild_id)
        else:
            return None

    def _delete_cached_guild(self, guild_id):
        """Removes a guild from the cache."""

        did_delete = True if self._guild_cache.pop(
            guild_id, None) is not None else False

        if did_delete:
            self.bot.logger.debug(
                f'Deleted cached user data for guild "{guild_id}".')

        return did_delete

    async def set_syncable_user(self, guild_id: str, user_id: str) -> None:
        guild_id = str(guild_id)
        guilds = [guild_id]
        user = await self.db.syncable.find_one({"_id": str(user_id)}) or None
        if user:
            guilds = guilds + user['guilds']

        await self.db.syncable.find_one_and_update(
            {"_id": str(user_id)},
            {"$set": {
                f"guilds": guilds
            }},
            upsert=True, return_document=ReturnDocument.AFTER
        )
    
    # TODO: Cache shit. Fetching DB every time someone joins is inefficient.
    async def syncable_user(self, user_id: str) -> int:
        user = await self.db.syncable.find_one({"_id": str(user_id)}) or {}
        return user.get('guilds')

    async def create_user(self, guild_id: str, user_id: str, pos=None) -> dict:
        """This creates a member, with the option to add their specific
        position into the database."""
        guild_id = str(guild_id)
        conf = await self.db.guild_config.find_one({"_id": str(guild_id)}) or {}

        if (await self.get_user(guild_id, user_id)):
            return None
        
        if pos and not (await Positions(self.bot).get_position(guild_id, pos)):
            return None

        user_id = str(user_id) # Just in case an integer is passed.
        positions = ["pos_" + pos] if pos else []
        user = {"user_id": user_id, "positions": positions}
        
        res = await self.db.guild_config.find_one_and_update(
            {"_id": str(guild_id)},
            {"$set": {
                f"users.{user_id}": user}},
            upsert=True, return_document=ReturnDocument.AFTER
            # This or is hopefully redundant due to the upsert flag, but
            # I'm just being cautious.
        ) or {}
        print(res)
        await self.set_syncable_user(guild_id, user_id)
        conf = await self.db.guild_config.find_one({"_id": str(guild_id)}) or {}
        self._cache_guild(guild_id, conf.get("users"))

        return True        

    async def get_user(self, guild_id: str, user_id: str) -> dict:
        """This fetches a member from the staff database."""
        guild_id = str(guild_id)
        users  = await self._get_guild_config(guild_id)
        if users:
            return users.get(str(user_id))
        else:
            return None

    async def add_user_pos(self, guild_id: str, user_id: str, pos: str) -> dict:
        """This adds a role to a user."""
        guild_id = str(guild_id)
        conf = await self.db.guild_config.find_one({"_id": str(guild_id)}) or {}
        user = await self.get_user(guild_id, user_id)
        if not (await Positions(self.bot).get_position(guild_id, pos)):
            return None
        if not user:
            return await self.create_user(guild_id, user_id, pos=pos)
    
        user['positions'].append("pos_" + pos)
        result = await self.db.guild_config.find_one_and_update(
            {"_id": str(guild_id)},
            {"$set": {
                f"users.{user_id}": user}},
            upsert=True, return_document=ReturnDocument.AFTER
            # This or is hopefully redundant due to the upsert flag, but
            # I'm just being cautious
        )
        self._cache_guild(guild_id, conf.get("users"))

        return result

    async def bulk_add_user_role(self, guild_id: str, user_id: str, pos: list) -> dict:
        """This adds a list of roles to a given position."""
        guild_id = str(guild_id)
        conf = await self.db.guild_config.find_one({"_id": str(guild_id)}) or {}
        user = await self.get_user(guild_id, user_id)
        if not user:
            return None
        for x in pos:
            if not (await Positions(self.bot).get_position(guild_id, x)):
                return x, None

        user['positions'] = user['positions'] + x
        result = await self.db.guild_config.find_one_and_replace(
            {f"{user_id}": user},
            {f"{user_id}": user},
            upsert=True, return_document=ReturnDocument.AFTER
            # This or is hopefully redundant due to the upsert flag, but
            # I'm just being cautious
        ) or {}
        self._cache_guild(guild_id, conf.get("users"))

        return result

    async def remove_user_role(self, guild_id: str, user_id: str, pos: str) -> dict:
        """This removes a role from a given position."""
        guild_id = str(guild_id)
        conf = await self.db.guild_config.find_one({"_id": str(guild_id)}) or {}
        user = await self.get_user(guild_id, user_id)
        if not user:
            raise UserNotFound("This user could not be found.")
        if not (await Positions(self.bot).get_position(guild_id, pos)):
            return None

        user['positions'].remove(pos)
        result = await self.db.guild_config.find_one_and_replace(
            {f"{user_id}": user},
            {f"{user_id}": user},
            upsert=True, return_document=ReturnDocument.AFTER
            # This or is hopefully redundant due to the upsert flag, but
            # I'm just being cautious
        ) or {}
        self._cache_guild(guild_id, conf.get("users"))

        return result
