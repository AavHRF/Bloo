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

    @tasks.loop(time=datetime.time(8, 0, 0, 0))
    async def daily_update(self):
        now_ts = datetime.datetime.now().timestamp()
        async with self.bot.session.get(
            "https://www.nationstates.net/pages/nations.xml.gz"
        ) as resp:
            with open("nations.xml.gz", "wb") as f:
                f.write(await resp.read())
        with gzip.open("nations.xml.gz", "rb") as f:
            tree = ElementTree.parse(f)
        root = tree.getroot()
        for nation in root.findall("NATION"):
            name = nation.find("NAME").text
            region = nation.find("REGION").text
            unstatus = nation.find("UNSTATUS").text
            endorsements = nation.find("ENDORSEMENTS").text if nation.find("ENDORSEMENTS") is not None else 0
            await self.bot.execute(
                "INSERT INTO nations (nation, region, unstatus, endorsements, last_update) VALUES ($1, $2, $3, $4, $5) ON CONFLICT (nation) DO UPDATE SET region = $2, unstatus = $3, endorsements = $4, last_update = $5",
                name,
                region,
                unstatus,
                endorsements,
                now_ts,
            )

        all_guilds = await self.bot.fetch("SELECT guild_id FROM nsv_settings")
        for guild in all_guilds:
            guild_id = guild["guild_id"]
            guild_obj = self.bot.get_guild(guild_id)
            if guild_obj is None:
                continue
            settings = await self.bot.fetch(
                "SELECT * FROM nsv_settings WHERE guild_id = $1", guild_id
            )
            if settings[0]["region"] is None:
                continue
            guild_members = await self.bot.fetch(
                "SELECT discord_id, nation FROM nsv_table WHERE guild_id = $1", guild_id
            )
            guest_role = guild_obj.get_role(settings[0]["guest_role"])
            wa_resident_role = guild_obj.get_role(settings[0]["wa_resident_role"])
            resident_role = guild_obj.get_role(settings[0]["resident_role"])
            for member in guild_members:
                discord_id = member["discord_id"]
                nation = member["nation"]
                # Check if the member is still in the guild
                member_obj = guild_obj.get_member(discord_id)
                if member_obj is None:
                    continue
                else:
                    vals = await self.bot.fetch(
                        "SELECT region, unstatus FROM nations WHERE nation = $1",
                        nation,
                    )
                    if not vals:
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


async def setup(bot: Bloo):
    await bot.add_cog(DailyUpdate(bot))


