import json
import aiohttp
import discord
import asyncio

from discord.ext import commands

API_BASE_URL = "http://api.staging.sfe.gg/"


class Invite:
    """This syncs the servers a member is in to the servers they're supposed to be in."""

    def __init__(self, api_token):
        self.api_token = api_token

    async def to_guild(self, guild_id: int, user_id: int, roles: list) -> dict:
        """This attempts to forceadd the member to the guild."""

        headers = {"Authorization": self.api_token,
                   "roles": str(roles)}

        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(API_BASE_URL + f"add/{guild_id}/{user_id}") as resp:
                res = await resp.json()

        if res["success"] and res["code"] == 0:
            return {"response": res["response"]}

        elif res['code'] == 1:
            return {"link": API_BASE_URL + f"code/{res['uuid']}", "response": res["response"]}

        elif res["success"] and res["code"] == 2:
            return {"server": True, "response": res["response"]}

        elif res['code'] == 30001:
            return {"max": True, "response": res["response"]}
        elif res['code'] == 40007:
            return {"banned": True, "response": res['response']}
        elif res['code'] == 50013:
            return {"no_perm": True, "response": res['response']}
        else:
            return {"response": res, "unknown": True}
