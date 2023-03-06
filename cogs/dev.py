import asyncio
import discord
import datetime
import gzip
from xml.etree import ElementTree
import os
from discord.ext import commands
from framework.bot import Bloo


class developer(commands.Cog):
    def __init__(self, bot: Bloo):
        self.bot = bot

    @commands.command(name="reload", description="Reload a cog.")
    @commands.is_owner()
    async def reload(self, ctx: commands.Context, *, cog: str):
        if "*" in cog:
            for filename in os.listdir("cogs"):
                if os.path.isfile(os.path.join("cogs", filename)):
                    if filename.endswith(".py"):
                        await self.bot.reload_extension(f"cogs.{filename[:-3]}")
            await ctx.send("Done!", ephemeral=True)
        else:
            for c in cog.split(","):
                await self.bot.reload_extension(f"cogs.{c.lower().replace(' ', '_')}")
            await ctx.send("Done!", ephemeral=True)

    @commands.command(name="load", description="Load a cog.")
    @commands.is_owner()
    async def load(self, ctx: commands.Context, cog: str):
        await self.bot.load_extension(f"cogs.{cog.lower().replace(' ', '_')}")
        await ctx.send("Done!", ephemeral=True)

    @commands.command(name="unload", description="Unload a cog.")
    @commands.is_owner()
    async def unload(self, ctx: commands.Context, cog: str):
        await self.bot.unload_extension(f"cogs.{cog.lower().replace(' ', '_')}")
        await ctx.send("Done!", ephemeral=True)

    @commands.command(name="say", description="Send a message to a channel.")
    @commands.is_owner()
    async def say(
        self, ctx: commands.Context, channel: discord.TextChannel, *, message: str
    ):
        await channel.send(message)
        await ctx.send("Done!", ephemeral=True)

    @commands.command()
    @commands.is_owner()
    async def sync(self, ctx: commands.Context, guild: int = None):
        if guild:
            await self.bot.tree.sync(guild=discord.Object(guild))
        else:
            await self.bot.tree.sync()
        await ctx.send(":arrows_counterclockwise:")

    def parse(self, f):
        return ElementTree.parse(f)

    # noinspection DuplicatedCode
    @commands.command()
    @commands.is_owner()
    async def daily_update(self, ctx: commands.Context):
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
                    if wa_resident_role in member.roles and wa_resident_role is not None:
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
                        if guest_role not in member_obj.roles and guest_role is not None:
                            await member_obj.add_roles(guest_role)
                        if wa_resident_role in member_obj.roles and wa_resident_role is not None:
                            await member_obj.remove_roles(wa_resident_role)
                        if resident_role in member_obj.roles and resident_role is not None:
                            await member_obj.remove_roles(resident_role)
                    else:
                        if vals[0]["unstatus"] == "WA Member":
                            status = "wa-resident"
                            if guest_role in member_obj.roles and guest_role is not None:
                                await member_obj.remove_roles(guest_role)
                            if wa_resident_role not in member_obj.roles and wa_resident_role is not None:
                                await member_obj.add_roles(wa_resident_role)
                            if resident_role not in member_obj.roles and resident_role is not None:
                                await member_obj.add_roles(resident_role)
                        else:
                            status = "resident"
                            if guest_role in member_obj.roles and guest_role is not None:
                                await member_obj.remove_roles(guest_role)
                            if resident_role not in member_obj.roles and resident_role is not None:
                                await member_obj.add_roles(resident_role)
                    await self.bot.execute(
                        "UPDATE nsv_table SET status = $1 WHERE discord_id = $2 AND guild_id = $3",
                        status,
                        discord_id,
                        guild_id,
                    )
            print(f"Updated {guild_obj.name} | ID: ({guild_id})")
        print("Finished update.")


    @commands.command()
    @commands.is_owner()
    async def nsl_update(self, ctx):
        now_ts = datetime.datetime.now()
        # Download the region dump
        # noinspection DuplicatedCode
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
                        log.write(f"{member.name} ({member.id}) | NO NATION VERIFIED | FOUNDER ROLE REMOVED\n")
                    if delegate_role in member.roles and senior not in member.roles:
                        log.write(f"{member.name} ({member.id}) | NO NATION VERIFIED | DELEGATE ROLE REMOVED\n")
                    if founder_role in member.roles and senior in member.roles:
                        log.write(f"{member.name} ({member.id}) | NO NATION VERIFIED | SENIOR FDR EXEMPT\n")
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
                            continue
                        if vals[0]["founder"] == record["nation"]:
                            founder = True
                        if vals[0]["wa_delegate"] == record["nation"]:
                            delegate = True
                    if not founder or not delegate:
                        if founder_role in member.roles and senior not in member.roles and not founder:
                            log.write(f"{member.name} ({member.id}) | FOUNDER ROLE REMOVED\n")
                        if delegate_role in member.roles and senior not in member.roles and not delegate:
                            log.write(f"{member.name} ({member.id}) | DELEGATE ROLE REMOVED\n")
                        continue
                    if founder:
                        if founder_role not in member.roles:
                            log.write(f"{member.name} ({member.id}) | FOUNDER ROLE ADDED\n")
                    else:
                        if (
                                founder_role in member.roles
                                and senior not in member.roles
                        ):
                            log.write(f"{member.name} ({member.id}) | FOUNDER ROLE REMOVED\n")
                        if (
                                founder_role in member.roles
                                and senior in member.roles
                        ):
                            log.write(f"{member.name} ({member.id}) | SENIOR FDR EXEMPT\n")
                    if delegate:
                        if delegate_role not in member.roles:
                            log.write(f"{member.name} ({member.id}) | DELEGATE ROLE ADDED\n")
                    else:
                        if (
                                delegate_role in member.roles
                                and senior not in member.roles
                        ):
                            log.write(f"{member.name} ({member.id}) | DELEGATE ROLE REMOVED\n")
                        if (
                                delegate_role in member.roles
                                and senior in member.roles
                        ):
                            log.write(f"{member.name} ({member.id}) | SENIOR DEL EXEMPT\n")
                    await console.send(
                        f"Updated {member.name} | ID: ({member.id}) STATUS "
                        f"({'FOUNDER' if founder else 'NONFOUNDER'}) ({'DELEGATE' if delegate else 'NONDELEGATE'})"
                    )
        log.close()
        await console.send("Done with NSL update.", file=discord.File("nsl_update.log"))
        print("Done with NSL update.")


async def setup(bot):
    await bot.add_cog(developer(bot))
