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

    async def setup_hook(self) -> None:
        self.pool = await asyncpg.create_pool(
            dsn=self.config["dsn"],
        )
        self.session = aiohttp.ClientSession(
            headers={
                "User-Agent": "Bloo NSV // v.1.0.0 // Owned by nation=united_calanworie"
            }
        )
        with open("tables.sql") as f:
            await self.pool.execute(f.read())

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

    async def fetch(self, query: str, *args) -> List[asyncpg.Record] | asyncpg.Record:
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
