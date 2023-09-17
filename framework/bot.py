import aiohttp
import asyncpg
import discord
import json
import os
from discord.ext import commands
from typing import Optional, List, Literal
from aiolimiter import AsyncLimiter


class Bloo(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="b>",
            intents=discord.Intents.all(),
            help_command=None,
        )
        self.scam_domains = None
        self.pool: Optional[asyncpg.Pool] = None
        self.config = json.load(open("config.json"))
        self.session = None
        self.limiter = AsyncLimiter(25, 30)
        """
        The watchlist is a dictionary with the following keys:
        - discord_ids: Set[int]
        - nation_names: Set[str]
        - known_names: Set[str]
        """
        self.watchlist = {}

    async def setup_hook(self) -> None:
        self.pool = await asyncpg.create_pool(
            dsn=self.config["dsn"],
        )
        self.session = aiohttp.ClientSession(
            headers={
                "User-Agent": "Bloo NSV // v.1.4.0 // Owned by nation=united_calanworie"
            }
        )
        # with open("tables.sql") as f:
        #     await self.pool.execute(f.read())

        for cog in os.listdir("cogs"):
            try:
                if cog.endswith(".py"):
                    await self.load_extension(f"cogs.{cog[:-3]}")
            except discord.ext.commands.errors.NoEntryPointError:
                pass
            except discord.ext.commands.errors.ExtensionFailed as e:
                print(e)
                pass

        self.scam_domains = json.load(open("scams.json"))["domains"]

        watchlist = await self.fetch("SELECT * FROM watchlist")
        discord_ids = set()
        nation_names = set()
        known_names = set()
        for record in watchlist:
            # TODO: Make this more efficient. Not a top priority as this only runs once on startup.
            # During bot runtime, the watchlist is stored in memory and persisted to the database by
            # the watchlist cog. This is only used to load the watchlist into memory on startup, and
            # therefore can suffer some performance hits for the sake of quick-and-dirty functionality.
            # It might be worth improving at some point though if startup times become an issue, but
            # that would only likely happen if the watchlist becomes very large. (Unlikely)
            for discord_id in record["known_ids"].split(","):
                try:
                    discord_ids.add(int(discord_id))
                except ValueError:
                    pass
            for nation_name in record["known_nations"].split(","):
                try:
                    nation_names.add(str(nation_name))
                except ValueError:
                    pass
            for known_name in record["known_names"].split(","):
                try:
                    known_names.add(str(known_name))
                except ValueError:
                    pass

        self.watchlist = {
            "discord_ids": discord_ids,
            "nation_names": nation_names,
            "known_names": known_names,
        }

    async def fetch(self, query: str, *args) -> List[asyncpg.Record]:
        con: asyncpg.Connection
        async with self.pool.acquire() as con:
            return await con.fetch(query, *args)

    async def execute(self, query: str, *args) -> str:
        con: asyncpg.Connection
        async with self.pool.acquire() as con:
            return await con.execute(query, *args)

    async def close(self) -> None:
        await self.pool.close()
        await self.session.close()
        await super().close()

    async def ns_request(
        self, payload: dict, mode: Literal["GET", "POST"]
    ) -> aiohttp.ClientResponse:
        async with self.limiter:
            if mode.upper() == "GET":
                return await self.session.get(
                    "https://www.nationstates.net/cgi-bin/api.cgi",
                    params=payload,
                )
            elif mode.upper() == "POST":
                return await self.session.post(
                    "https://www.nationstates.net/cgi-bin/api.cgi",
                    data=payload,
                )

    def run(self, *args, **kwargs) -> None:
        super().run(self.config["token"])
