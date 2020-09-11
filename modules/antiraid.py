import time
import discord

from enum import Enum
from discord.ext import commands

from struc.commands import CustomCommand, CustomGroup


class Flags(Enum):
    EMPLOYEE = 1
    PARTNER = 2
    HYPESQUAD_EVENTS = 4
    BUG_HUNTER = 8
    HYPESQUAD_BRAVERY = 64
    HYPESQUAD_BRILLIANCE = 128
    HYPESQUAD_BALANCE = 256
    EARLY_SUPPORTER = 512
    BUG_HUNTER_TIER_TWO = 16384


class AntiRaid(commands.Cog, name="Antiraid"):

    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db
        self.guild_cache = {}
        self.raid_cache = {}
        self.rate = 5.0
        self.per = 8.0
        self.allowance = self.rate
        self.last_check = time.time()
        self.last_five = []
        self.sample = []
        self.check_once = False

    async def get_guild_config(self, guild_id: int):
        """Fetch the antiraid config of the specified guild ID."""

        # Check if fresh document exists in the cache.
        cached_guild = self.get_cached_guild(guild_id)
        if cached_guild:
            return cached_guild

        conf = await self.db.guild_config.find_one({"_id": str(guild_id)}) or {}

        if conf.get("antiraid"):
            self.cache_guild(guild_id, conf.get("antiraid"))

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

    def do_suspicious_check(self, member_dict: dict) -> int:
        """This determines if an account is suspicious and returns a confidence level from 0 - 1."""
        confidence = 1

        # Checks their flags.
        flags = []
        high_value_flags = ['HYPESQUAD_EVENTS', 'PARTNER', 'EMPLOYEE', 'VERIFIED_BOT_DEVELOPER', 'BUG_HUNTER', 'BUG_HUNTER_TIER_TWO']
        for flag in Flags:
            if member_dict.get('public_flags') & flag.value:
                flags.append(flag.name)
        high_value = any(x == flag for flag in flags for x in high_value_flags)

        if high_value:
            confidence = confidence - .99

        # Checks their creation date.
        month_old_check = (time.time() - member_dict.get('created_at').timestamp()) >= 2419200

        year_old_check = (time.time() - member_dict.get('created_at').timestamp()) >= 31536000

        if year_old_check:
            confidence = confidence - .4
        elif month_old_check:
            confidence = confidence - .1

        # Checks if their profile picture is animated.
        is_avatar_animated = member_dict.get('is_avatar_animated')

        if is_avatar_animated:
            confidence = confidence - .95

        # Checks if they have a status.
        has_activity = True if member_dict.get("activity") else False

        # Checks if they have more than one status.
        has_multiple_activities = True if member_dict.get('activities') and member_dict.get('activities') > 1 else False

        if has_activity:
            if has_multiple_activities:
                confidence = confidence - .95
            else:
                confidence = confidence - .70

        # Checks if they're on mobile.
        is_on_mobile = member_dict.get('is_on_mobile')

        if is_on_mobile:
            confidence = confidence - .40

        return max(0, confidence)

    def do_age_comparison(self, members: list) -> list:
        """Compares the account creation dates of a list of members"""
        match = False
        x = 0
        matched = []
        while not match:
            count = len(members)
            if x > count:
                break
            sample = members[x]
            x += 1
            for account in members:
                if account == sample:
                    continue
                if abs(account.get('created_at').timestamp() - sample.get('created_at').timestamp()) <= 86400:
                    match = True
                    matched.append(account)

            if match:
                break
        return matched

    @commands.group(cls=CustomGroup)
    async def antiraid(self, ctx) -> None:
        """The antiraid commands."""
        return

    @antiraid.command(cls=CustomCommand)
    async def on(self, ctx) -> None:
        raise NotImplementedError

    @commands.Cog.listener()
    async def on_fake_event(self, member: discord.Member):
        current = time.time()

        db = await self.get_guild_config(member.guild.id)
        if not db or not db.get("enabled"):
            return

        time_passed = current - self.last_check
        self.last_check = current
        self.allowance += time_passed * (self.rate / self.per)
        member_dict = {
            'id': member.id,
            'username': str(member),
            'created_at': member.created_at,
            'joined_at': member.joined_at,
            'is_avatar_animated': member.is_avatar_animated(),
            'activity': member.activity,
            'activities': member.activities,
            'is_on_mobile': member.is_on_mobile(),
            'public_flags': member.public_flags  # NOTE: Requires discord.py 1.4+
        }
        if len(self.last_five) <= 5:
            self.last_five.append(member_dict)
        if self.allowance > self.rate:
            self.allowance = self.rate  # throttle
        if self.allowance < 1.0:
            if not self.check_once:
                last_five = self.do_age_comparison(self.last_five)  # To see if they all have the sameish creation date.
                if not len(last_five):
                    # Do notification here
                    return
                for account in last_five:
                    sus = self.do_suspicious_check(account)
                    if sus >= 0.5:
                        self.raid_cache[member.guild.id]['raiders'].append(account)
                self.check_once = True
                self.sample.append(account)
            else:
                if len(self.sample):
                    compare = self.sample
                    compare.append(member_dict)
                    if len(self.do_age_comparison(compare)):
                        sus = self.do_suspicious_check(member_dict)  # Just to prevent any false positives.
                        if sus >= 0.5:
                            self.raid_cache[member.guild.id]['raiders'].append(member_dict)
                else:
                    return  # If check once has been hit and there's no sample, the age comparison must've failed so nothing to do.
        else:
            self.allowance -= 1.0
            if self.last_five >= 5:
                self.last_five = [member_dict]  # Clear the last five, but keep the most recent one. Just in case.

    @commands.Cog.listener()
    async def on_test_event(self, member: discord.Member):
        antiraid = await self.get_guild_config(member.guild.id)
        if not antiraid:
            return
        if not antiraid.get('member_join_count'):
            update = {"count": 1, "last_refreshed": str(round(time.time()))}
        else:
            last_refreshed = antiraid['member_join_count']['last_refreshed']
            if round(time.time()) - int(last_refreshed) >= 10:
                update = {"count": 1, "last_refreshed": str(round(time.time()))}
            else:
                count = antiraid['member_join_count']['count'] + 1
                update = {"count": count, "last_refreshed": str(round(time.time()))}

        await self.db.guild_config.find_one_and_update(
            {"_id": str(member.guild.id)},
            {"$set": {
                "antiraid.member_join_count": update
            }}
        )
        print('test_event')


def setup(bot):
    # bot.add_cog(AntiRaid(bot))
    pass
