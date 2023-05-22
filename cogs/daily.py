import asyncio
import discord
import datetime
import gzip
import json
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
                "SELECT discord_id FROM nsv_table WHERE guild_id = $1", guild_id
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
                        await member.remove_roles(verified_role, reason="No nation verified")
                    if guest_role in member.roles and guest_role is not None:
                        await member.remove_roles(guest_role, reason="No nation verified")
                    if (
                        wa_resident_role in member.roles
                        and wa_resident_role is not None
                    ):
                        await member.remove_roles(wa_resident_role, reason="No nation verified")
                    if resident_role in member.roles and resident_role is not None:
                        await member.remove_roles(resident_role, reason="No nation verified")
            for member in guild_obj.members:
                if settings[0]["region"] and len(settings[0]["region"].split(",")) > 1:
                    set_region = settings[0]["region"].split(",")
                    set_region = [x.strip() for x in set_region]
                else:
                    set_region = [settings[0]["region"].strip() if settings[0]["region"] else None]
                discord_id = member.id
                status = "guest"
                vals = await self.bot.fetch(
                    "SELECT * FROM nsv_table WHERE discord_id = $1 AND guild_id = $2",
                    discord_id,
                    guild_id,
                )
                if not vals:
                    print("No nations found, skipping...")
                    continue
                else:
                    for val in vals:
                        record = await self.bot.fetch(
                            "SELECT * FROM nation_dump WHERE nation = $1",
                            val["nation"],
                        )
                        if not record:
                            print("Nation has CTEd, skipping...")
                            continue
                        else:
                            if record[0]["region"] in set_region:
                                status = "resident"
                                if record[0]["unstatus"] == "WA Member":
                                    status = "wa-resident"

                if status == "guest":
                    if (
                        guest_role not in member.roles
                        and guest_role is not None
                    ):
                        await member.add_roles(guest_role)
                    if (
                        wa_resident_role in member.roles
                        and wa_resident_role is not None
                    ):
                        await member.remove_roles(wa_resident_role)
                    if (
                        resident_role in member.roles
                        and resident_role is not None
                    ):
                        await member.remove_roles(resident_role)
                else:
                    if status == "wa-resident":
                        if (
                            guest_role in member.roles
                            and guest_role is not None
                        ):
                            await member.remove_roles(guest_role)
                        if (
                            wa_resident_role not in member.roles
                            and wa_resident_role is not None
                        ):
                            await member.add_roles(wa_resident_role)
                        if (
                            resident_role not in member.roles
                            and resident_role is not None
                        ):
                            await member.add_roles(resident_role)
                    else:
                        if (
                            guest_role in member.roles
                            and guest_role is not None
                        ):
                            await member.remove_roles(guest_role)
                        if (
                            resident_role not in member.roles
                            and resident_role is not None
                        ):
                            await member.add_roles(resident_role)
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
                "INSERT INTO nsl_region_table (region, founder, wa_delegate, delegatevotes, numnations, inserted_at) VALUES ($1, $2, $3, $4, $5, $6)",
                name,
                founder,
                delegate,
                int(delegatevotes),
                int(numnations),
                now_ts,
            )
        log = open("nsl_update.log", "a")
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
                        log.write(f"{member.name} ({member.id}) | NO NATION VERIFIED | GOVERNOR ROLE REMOVED\n")
                        await member.remove_roles(founder_role)
                    if delegate_role in member.roles and senior not in member.roles:
                        log.write(f"{member.name} ({member.id}) | NO NATION VERIFIED | DELEGATE ROLE REMOVED\n")
                        await member.remove_roles(delegate_role)
                    if founder_role in member.roles and senior in member.roles:
                        log.write(f"{member.name} ({member.id}) | NO NATION VERIFIED | SENIOR GVNR EXEMPT\n")
                    if delegate_role in member.roles and senior in member.roles:
                        log.write(f"{member.name} ({member.id}) | NO NATION VERIFIED | SENIOR DEL EXEMPT\n")
                else:
                    founder = False
                    delegate = False
                    for record in mem:
                        vals = await self.bot.fetch(
                            "SELECT * FROM nsl_region_table WHERE founder = $1 OR wa_delegate = $1 ORDER BY inserted_at DESC LIMIT 1",
                            record["nation"],
                        )
                        if not vals:
                            log.write(f"{member.name} ({member.id}) NATION: {record['nation']}| NO REGION RECORDS FOUND\n")
                            continue
                        if vals[0]["founder"] == record["nation"]:
                            founder = True
                        if vals[0]["wa_delegate"] == record["nation"]:
                            delegate = True
                    if not founder or not delegate:
                        if founder_role in member.roles and senior not in member.roles and not founder:
                            log.write(f"{member.name} ({member.id}) | GOVERNOR ROLE REMOVED\n")
                            await member.remove_roles(founder_role)
                        if delegate_role in member.roles and senior not in member.roles and not delegate:
                            log.write(f"{member.name} ({member.id}) | DELEGATE ROLE REMOVED\n")
                            await member.remove_roles(delegate_role)
                        continue
                    if founder:
                        if founder_role not in member.roles:
                            log.write(f"{member.name} ({member.id}) | GOVERNOR ROLE ADDED\n")
                            await member.add_roles(founder_role)
                        if founder_role in member.roles:
                            log.write(f"{member.name} ({member.id}) | GVNR ROLE EXISTS\n")
                    else:
                        if (
                                founder_role in member.roles
                                and senior not in member.roles
                        ):
                            log.write(f"{member.name} ({member.id}) | GOVERNOR ROLE REMOVED\n")
                            await member.remove_roles(founder_role)
                        if (
                                founder_role in member.roles
                                and senior in member.roles
                        ):
                            log.write(f"{member.name} ({member.id}) | SENIOR GVNR EXEMPT\n")
                    if delegate:
                        if delegate_role not in member.roles:
                            log.write(f"{member.name} ({member.id}) | DELEGATE ROLE ADDED\n")
                            await member.add_roles(delegate_role)
                        if delegate_role in member.roles:
                            log.write(f"{member.name} ({member.id}) | DEL ROLE EXISTS\n")
                    else:
                        if (
                                delegate_role in member.roles
                                and senior not in member.roles
                        ):
                            log.write(f"{member.name} ({member.id}) | DELEGATE ROLE REMOVED\n")
                            await member.remove_roles(delegate_role)
                        if (
                                delegate_role in member.roles
                                and senior in member.roles
                        ):
                            log.write(f"{member.name} ({member.id}) | SENIOR DEL EXEMPT\n")
                    await console.send(
                        f"Updated {member.name} | ID: ({member.id}) STATUS "
                        f"({'FOUNDER' if founder else 'NONFOUNDER'}) ({'DELEGATE' if delegate else 'NONDELEGATE'})"
                    )
                    log.write(
                        f"Updated {member.name} | ID: ({member.id}) STATUS "
                        f"({'FOUNDER' if founder else 'NONFOUNDER'}) ({'DELEGATE' if delegate else 'NONDELEGATE'})"
                    )
        log.close()
        await console.send("Done with NSL update.", file=discord.File("nsl_update.log"))
        print("Done with NSL update.")

    @tasks.loop(time=datetime.time(0, 0, 0))
    async def update_scam_lists(self):
        async with self.bot.session.get(
            "https://raw.githubusercontent.com/nikolaischunk/discord-phishing-links/main/domain-list.json"
        ) as r:
            self.bot.scam_domains = await r.json()["domains"]
            with open("scams.json", "w") as f:
                json.dump(self.bot.scam_domains, f)

    @daily_update.before_loop
    async def before_daily_update(self):
        await self.bot.wait_until_ready()

    @update_scam_lists.before_loop
    async def before_update_scam_lists(self):
        await self.bot.wait_until_ready()


async def setup(bot: Bloo):
    await bot.add_cog(DailyUpdate(bot))
