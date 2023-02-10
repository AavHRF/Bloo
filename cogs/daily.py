import asyncio
import discord
import datetime
import gzip
from discord.ext import commands
from discord.ext import tasks
from framework.bot import Bloo
from xml.etree import ElementTree


class DailyUpdate(commands.Cog):
    def __init__(self, bot: Bloo):
        self.bot = bot
        self.daily_update.start()

    def cog_unload(self):
        self.daily_update.cancel()

    # noinspection DuplicatedCode
    @tasks.loop(time=datetime.time(8, 0, 0, 0))
    async def daily_update(self):
        now_ts = datetime.datetime.now()
        async with self.bot.session.get(
            "https://www.nationstates.net/pages/nations.xml.gz"
        ) as resp:
            with open("nations.xml.gz", "wb") as f:
                f.write(await resp.read())
        with gzip.open("nations.xml.gz", "rb") as f:
            tree = await asyncio.to_thread(self.parse, f)
            root = tree.getroot()
            for nation in root.findall("NATION"):
                name = nation.find("NAME").text.lower().replace(" ", "_")
                region = nation.find("REGION").text.lower().replace(" ", "_")
                unstatus = nation.find("UNSTATUS").text
                endorsements = (
                    nation.find("ENDORSEMENTS").text
                    if nation.find("ENDORSEMENTS") is not None
                    else 0
                )
                await self.bot.execute(
                    "INSERT INTO nation_dump (nation, region, unstatus, endorsements, last_update) VALUES ($1, $2, $3, $4, $5) ON CONFLICT (nation) DO UPDATE SET region = $2, unstatus = $3, endorsements = $4, last_update = $5",
                    name,
                    region,
                    unstatus,
                    endorsements,
                    now_ts,
                )
        all_guilds = await self.bot.fetch("SELECT guild_id FROM nsv_settings")
        for guild in all_guilds:
            guild_id = guild["guild_id"]
            guild_obj: discord.Guild = self.bot.get_guild(guild_id)
            if guild_obj is None:
                print("Could not find guild, skipping...")
                continue
            if not guild_obj.chunked:
                await guild_obj.chunk()
            print(f"Now updating {guild_obj.name} | ID: ({guild_id})")
            settings = await self.bot.fetch(
                "SELECT * FROM nsv_settings WHERE guild_id = $1", guild_id
            )
            if settings[0]["region"] is None:
                continue
            guild_members = await self.bot.fetch(
                "SELECT discord_id, nation FROM nsv_table WHERE guild_id = $1", guild_id
            )
            print(len(guild_members))
            guest_role = guild_obj.get_role(settings[0]["guest_role"])
            wa_resident_role = guild_obj.get_role(settings[0]["wa_resident_role"])
            resident_role = guild_obj.get_role(settings[0]["resident_role"])
            for member in guild_members:
                discord_id = member["discord_id"]
                nation = member["nation"]
                # Check if the member is still in the guild
                member_obj = guild_obj.get_member(discord_id)
                if member_obj is None:
                    print(f"Could not find member for ID {discord_id}")
                    member_obj = await self.bot.fetch_user(discord_id)
                else:
                    print(f"Checking {nation} | ID: ({discord_id})")
                    vals = await self.bot.fetch(
                        "SELECT region, unstatus FROM nation_dump WHERE nation = $1",
                        nation,
                    )
                    if not vals:
                        print("Nation not found, skipping...")
                        continue
                    if vals[0]["region"] != settings[0]["region"]:
                        status = "guest"
                        if guest_role not in member_obj.roles:
                            await member_obj.add_roles(guest_role)
                        if wa_resident_role in member_obj.roles:
                            await member_obj.remove_roles(wa_resident_role)
                        if resident_role in member_obj.roles:
                            await member_obj.remove_roles(resident_role)
                    else:
                        if vals[0]["unstatus"] == "WA Member":
                            status = "wa-resident"
                            if guest_role in member_obj.roles:
                                await member_obj.remove_roles(guest_role)
                            if wa_resident_role not in member_obj.roles:
                                await member_obj.add_roles(wa_resident_role)
                            if resident_role not in member_obj.roles:
                                await member_obj.add_roles(resident_role)
                        else:
                            status = "resident"
                            if guest_role in member_obj.roles:
                                await member_obj.remove_roles(guest_role)
                            if resident_role not in member_obj.roles:
                                await member_obj.add_roles(resident_role)
                    await self.bot.execute(
                        "UPDATE nsv_table SET status = $1 WHERE discord_id = $2 AND guild_id = $3",
                        status,
                        discord_id,
                        guild_id,
                    )
            print(f"Updated {guild_obj.name} | ID: ({guild_id})")
        print("Finished update.")

    @daily_update.before_loop
    async def before_daily_update(self):
        await self.bot.wait_until_ready()


async def setup(bot: Bloo):
    await bot.add_cog(DailyUpdate(bot))
