import asyncio
import aiohttp
import discord
from discord.ext import commands
from discord import app_commands
from xml.etree import ElementTree
from framework.bot import Bloo


class NSV(commands.Cog):
    def __init__(self, bot: Bloo):
        self.bot = bot

    async def auth_call(self, nation: str, token: str) -> bool:
        print(f"auth_call({nation}, {token})")
        resp: aiohttp.ClientResponse = await self.bot.ns_request(
            {
                "a": "verify",
                "nation": nation,
                "checksum": token,
            },
            "GET",
        )
        if not resp.ok:
            print("not ok")
            return False
        data = await resp.text()
        if "1" in data:
            print("ok")
            return True
        print("2nd not ok")
        return False

    async def auth_flow(self, ctx: commands.Context, nation: str):
        settings = await self.bot.fetch(
            "SELECT * FROM nsv_settings WHERE guild_id = $1",
            ctx.guild.id,
        )
        welcome_message = (
            settings[0]["welcome_message"]
            if settings[0]["welcome_message"]
            else "Welcome! Roles granted."
        )
        if not settings:
            await ctx.send("This server has not been set up yet for NSV.")
            return
        await ctx.author.send(
            f"Please log into {nation.replace('_', ' ').title()} now. Once you have done so, open this link: "
            f"https://nationstates.net/page=verify_login"
        )
        await ctx.author.send(
            "Copy the code from that page and paste it here. **__This code does not give anyone access to your "
            "nation, any form of control over it, etc. It ONLY allows verification of ownership.__**"
        )
        await ctx.send("Check your DMs!")
        try:
            msg: discord.Message = await self.bot.wait_for(
                "message",
                check=lambda m: m.author == ctx.author
                and m.channel == ctx.author.dm_channel,
                timeout=60,
            )
        except asyncio.TimeoutError:
            await ctx.author.send("Timed out.")
            return
        print("got token")
        print(nation)
        if not await self.auth_call(nation, msg.content):
            await ctx.author.send("Invalid code.")
            return
        guildbans = await self.bot.fetch(
            "SELECT * FROM nsv_ban_table WHERE guild_id = $1", ctx.guild.id
        )
        welcset = await self.bot.fetch(
            "SELECT * FROM welcome_settings WHERE guild_id = $1", ctx.guild.id
        )
        if not guildbans:
            pass

        for ban in guildbans:
            if nation == ban["nation"]:
                await ctx.author.ban(reason=ban["reason"])
                embed = discord.Embed(
                    title="Member joined with banned nation.",
                    description=f"User {ctx.author.mention} ({ctx.author.id}) joined with a nation ({nation.replace('_', '_').title()})that is banned from this server.",
                    color=discord.Color.red(),
                )
                await ctx.guild.get_channel(welcset[0]["welcome_channel"]).send(
                    embed=embed
                )
                return

        # Now that we have verified the user, we want to check residency / WA status
        resp: aiohttp.ClientResponse = await self.bot.ns_request(
            {
                "nation": nation,
                "q": "region+wa",
            },
            "GET",
        )
        if not resp.ok:
            await ctx.author.send("An error occurred.")
            return
        data = await resp.text()
        root = ElementTree.fromstring(data)
        region = root.find("REGION").text.lower().replace(" ", "_")
        wa = root.find("UNSTATUS").text
        status = None
        if settings[0]["region"]:
            if settings[0]["region"] != region:
                status = "guest"
            else:
                if "WA" in wa:
                    status = "wa-resident"
                else:
                    status = "resident"
            await self.bot.execute(
                "INSERT INTO nsv_table (discord_id, nation, guild_id, status) VALUES ($1, $2, $3, $4) ON CONFLICT (discord_id, guild_id) DO UPDATE SET nation = $2, status = $4",
                ctx.author.id,
                nation,
                ctx.guild.id,
                status,
            )
            verified_role = ctx.guild.get_role(settings[0]["verified_role"])
            if status == "guest":
                guest_role = ctx.guild.get_role(settings[0]["guest_role"])
                if not guest_role:
                    pass
                else:
                    await ctx.author.add_roles(
                        verified_role, guest_role, reason="Verified via NSV."
                    )
            else:
                resident_role = ctx.guild.get_role(settings[0]["resident_role"])
                if not resident_role:
                    pass
                else:
                    await ctx.author.add_roles(
                        verified_role, resident_role, reason="Verified via NSV."
                    )
                    if status == "wa-resident":
                        wa_resident_role = ctx.guild.get_role(
                            settings[0]["wa_resident_role"]
                        )
                        if not wa_resident_role:
                            pass
                        else:
                            await ctx.author.add_roles(
                                wa_resident_role, reason="Verified via NSV."
                            )
            await ctx.author.send(welcome_message)

        else:
            verified = ctx.guild.get_role(settings[0]["verified_role"])
            await ctx.author.add_roles(verified, reason="Verified via NSV.")

    @commands.guild_only()
    @app_commands.guild_only()
    @commands.hybrid_command(with_app_command=True)
    @commands.cooldown(1, 60, commands.BucketType.user)
    @app_commands.describe(
        nation="Your nation on nationstates.net. Do not include the pretitle."
    )
    async def verify(self, ctx: commands.Context, *, nation: str):
        """
        Verify your nation
        """
        if nation is not None:
            await self.auth_flow(ctx, nation.lower().replace(" ", "_"))
        else:
            await ctx.author.send(
                "Please enter your nation name. Do not include the pretitle, so The Grand Republic of Mynation would "
                "be Mynation."
            )
            try:
                msg: discord.Message = await self.bot.wait_for(
                    "message",
                    check=lambda m: m.author == ctx.author
                    and m.channel == ctx.author.dm_channel,
                    timeout=60,
                )
            except asyncio.TimeoutError:
                await ctx.send("Timed out.")
                return
            await self.auth_flow(ctx, str(msg.clean_content).lower().replace(" ", "_"))

    @commands.guild_only()
    @commands.hybrid_command(with_app_command=True)
    async def drop(self, ctx: commands.Context):
        """
        Drops your nation for the server.
        """
        await self.bot.execute(
            "DELETE FROM nsv_table WHERE discord_id = $1 AND guild_id = $2",
            ctx.author.id,
            ctx.guild.id,
        )
        await ctx.send("Done.")


async def setup(bot: Bloo):
    await bot.add_cog(NSV(bot))
