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

    @staticmethod
    def parse(f):
        return ElementTree.parse(f)

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
            if not settings[0]["force_verification"]:
                continue
            guild_members = await self.bot.fetch(
                "SELECT discord_id, nation FROM nsv_table WHERE guild_id = $1", guild_id
            )
            print(len(guild_members))
            guest_role = guild_obj.get_role(settings[0]["guest_role"])
            wa_resident_role = guild_obj.get_role(settings[0]["wa_resident_role"])
            resident_role = guild_obj.get_role(settings[0]["resident_role"])
            verified_role = guild_obj.get_role(settings[0]["verified_role"])
            if any(
                [
                    guest_role is None,
                    wa_resident_role is None,
                    resident_role is None,
                    verified_role is None,
                ]
            ):
                print("At least one role in this guild is not set!")
            for member in guild_obj.members:
                if member.id not in [m["discord_id"] for m in guild_members]:
                    if verified_role in member.roles and verified_role is not None:
                        await member.remove_roles(verified_role)
                    if guest_role in member.roles and guest_role is not None:
                        await member.remove_roles(guest_role)
                    if (
                        wa_resident_role in member.roles
                        and wa_resident_role is not None
                    ):
                        await member.remove_roles(wa_resident_role)
                    if resident_role in member.roles and resident_role is not None:
                        await member.remove_roles(resident_role)
            for member in guild_members:
                discord_id = member["discord_id"]
                nation = member["nation"]
                # Check if the member is still in the guild
                member_obj = guild_obj.get_member(discord_id)
                if member_obj is None:
                    print(f"Could not find member for ID {discord_id}")
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
                        if (
                            guest_role not in member_obj.roles
                            and guest_role is not None
                        ):
                            await member_obj.add_roles(guest_role)
                        if (
                            wa_resident_role in member_obj.roles
                            and wa_resident_role is not None
                        ):
                            await member_obj.remove_roles(wa_resident_role)
                        if (
                            resident_role in member_obj.roles
                            and resident_role is not None
                        ):
                            await member_obj.remove_roles(resident_role)
                    else:
                        if vals[0]["unstatus"] == "WA Member":
                            status = "wa-resident"
                            if (
                                guest_role in member_obj.roles
                                and guest_role is not None
                            ):
                                await member_obj.remove_roles(guest_role)
                            if (
                                wa_resident_role not in member_obj.roles
                                and wa_resident_role is not None
                            ):
                                await member_obj.add_roles(wa_resident_role)
                            if (
                                resident_role not in member_obj.roles
                                and resident_role is not None
                            ):
                                await member_obj.add_roles(resident_role)
                        else:
                            status = "resident"
                            if (
                                guest_role in member_obj.roles
                                and guest_role is not None
                            ):
                                await member_obj.remove_roles(guest_role)
                            if (
                                resident_role not in member_obj.roles
                                and resident_role is not None
                            ):
                                await member_obj.add_roles(resident_role)
                    await self.bot.execute(
                        "UPDATE nsv_table SET status = $1 WHERE discord_id = $2 AND guild_id = $3",
                        status,
                        discord_id,
                        guild_id,
                    )
            print(f"Updated {guild_obj.name} | ID: ({guild_id})")
        print("Finished daily update.")
        print("Starting NSL update...")
        # Download the region dump
        async with self.bot.session.get(
            "https://www.nationstates.net/pages/regions.xml.gz"
        ) as resp:
            if resp.status != 200:
                print("Could not download region dump!")
                return
            with open("regions.xml.gz", "wb") as f:
                f.write(await resp.read())
        # Unzip the file
        with gzip.open("regions.xml.gz", "rb") as f_in:
            # Read the file into etree
            tree = await asyncio.to_thread(self.parse, f_in)
        # Get the root element
        root = tree.getroot()
        for region in root.findall("REGION"):
            name = region.find("NAME").text
            founder = region.find("FOUNDER").text
            delegate = region.find("DELEGATE").text
            delegatevotes = region.find("DELEGATEVOTES").text
            numnations = region.find("NUMNATIONS").text
            await self.bot.execute(
                "INSERT INTO nsl_region_dump (region, founder, delegate, delegatevotes, numnations) VALUES ($1, $2, $3, $4, $5)",
                name,
                founder,
                delegate,
                delegatevotes,
                numnations,
                now_ts,
            )
        print("Finished updating NSL region dump.")
        print("Updating server roles...")
        nsl_update = False  # Temporary guard to prevent NSL update from running while people verify
        if nsl_update:
            nsl = self.bot.get_guild(414822188273762306)
            console = nsl.get_channel(626654671167160320)
            founder_role = nsl.get_role(414822833873747984)
            delegate_role = nsl.get_role(622961669634785302)
            senior = nsl.get_role(
                414871607736008715
            )  # Seniors are immune to losing their roles
            await nsl.chunk()  # Ensure that NSL is in the cache so that we can update the members properly
            for member in nsl.members:
                if member.bot:
                    continue
                else:
                    mem = await self.bot.fetch(
                        "SELECT nation FROM nsl_table WHERE discord_id = $1", member.id
                    )
                    if not mem:
                        # Gotta be verified to have roles! Unless you're a senior... then you're exempt. That's a
                        # sekrit tho.
                        if founder_role in member.roles and senior not in member.roles:
                            await member.remove_roles(founder_role)
                        if delegate_role in member.roles and senior not in member.roles:
                            await member.remove_roles(delegate_role)
                    else:
                        if len(mem) == 1:
                            vals = await self.bot.fetch(
                                "SELECT * FROM nsl_region_dump WHERE founder OR delegate = $1",
                                mem[0]["nation"],
                            )
                            if not vals:
                                if founder_role in member.roles and senior not in member.roles:
                                    await member.remove_roles(founder_role)
                                if delegate_role in member.roles and senior not in member.roles:
                                    await member.remove_roles(delegate_role)
                                continue

                            if vals[0]["founder"] == nation:
                                if founder_role not in member.roles:
                                    await member.add_roles(founder_role)
                            else:
                                if (
                                    founder_role in member.roles
                                    and senior not in member.roles
                                ):
                                    await member.remove_roles(founder_role)
                            if vals[0]["delegate"] == nation:
                                if delegate_role not in member.roles:
                                    await member.add_roles(delegate_role)
                            else:
                                if (
                                    delegate_role in member.roles
                                    and senior not in member.roles
                                ):
                                    await member.remove_roles(delegate_role)
                            await console.send(
                                f"Updated {member.name} | ID: ({member.id}) STATUS "
                                f"({vals[0]['founder']}) ({vals[0]['delegate']})"
                            )
                        else:
                            # There are multiple records for this member
                            # Iterate through each record and check if the nation is a founder or delegate
                            # If it is, add the role
                            # If it isn't, remove the role
                            founder = False
                            delegate = False
                            for record in mem:
                                vals = await self.bot.fetch(
                                    "SELECT * FROM nsl_region_dump WHERE founder OR delegate = $1",
                                    record["nation"],
                                )
                                if vals[0]["founder"] == nation:
                                    founder = True
                                if vals[0]["delegate"] == nation:
                                    delegate = True
                            if not founder or not delegate:
                                if founder_role in member.roles and senior not in member.roles and not founder:
                                    await member.remove_roles(founder_role)
                                if delegate_role in member.roles and senior not in member.roles and not delegate:
                                    await member.remove_roles(delegate_role)
                                continue
                            if founder:
                                if founder_role not in member.roles:
                                    await member.add_roles(founder_role)
                            else:
                                if (
                                    founder_role in member.roles
                                    and senior not in member.roles
                                ):
                                    await member.remove_roles(founder_role)
                            if delegate:
                                if delegate_role not in member.roles:
                                    await member.add_roles(delegate_role)
                            else:
                                if (
                                    delegate_role in member.roles
                                    and senior not in member.roles
                                ):
                                    await member.remove_roles(delegate_role)
                            await console.send(
                                f"Updated {member.name} | ID: ({member.id}) STATUS "
                                f"({'FOUNDER' if founder else 'NONFOUNDER'}) ({'DELEGATE' if delegate else 'NONDELEGATE'})"
                            )
            print("Done with NSL update.")

    @daily_update.before_loop
    async def before_daily_update(self):
        await self.bot.wait_until_ready()


async def setup(bot: Bloo):
    await bot.add_cog(DailyUpdate(bot))
