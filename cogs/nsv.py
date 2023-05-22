import asyncio
import aiohttp
import discord
from discord.ext import commands
from discord import app_commands
from xml.etree import ElementTree
from framework.bot import Bloo


class DropSelect(discord.ui.Select):

    def __init__(self, bot: Bloo, natlist: list, message: discord.Message):
        super().__init__(placeholder="Select a nation")
        self.bot = bot
        self.natlist = natlist
        self.message = message
        for nation in natlist[:24]:
            self.add_option(label=nation.replace('_', ' ').title(), value=nation)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await self.bot.execute(
            "DELETE FROM nsl_table WHERE discord_id = $1 AND nation = $2",
            interaction.user.id,
            self.values[0],
        )
        self.view.stop()
        self.disabled = True
        await self.message.edit(view=self.view)
        await interaction.followup.send(
            f"Removed {self.values[0].replace('_', ' ').title()} from your list of nations.",
            ephemeral=True,
        )


class DropView(discord.ui.View):

    def __init__(self, bot: Bloo, natlist: list, message: discord.Message):
        super().__init__()
        self.add_item(DropSelect(bot, natlist, message))


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
        await ctx.send("Check your DMs!", ephemeral=True)
        try:
            msg: discord.Message = await self.bot.wait_for(
                "message",
                check=lambda m: m.author == ctx.author
                                and m.channel == ctx.author.dm_channel,
                timeout=180,
            )
        except asyncio.TimeoutError:
            await ctx.author.send("Timed out.")
            return

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
        if ctx.guild.id == 414822188273762306:
            rresp = await self.bot.ns_request(
                {
                    "region": region,
                    "q": "founder+delegate",
                },
                "GET",
            )
            if not rresp.ok:
                await ctx.author.send("An error occurred.")
                return

            rroot = ElementTree.fromstring(await rresp.text())
            rgovernor = rroot.find("GOVERNOR").text
            rdelegate = rroot.find("DELEGATE").text
            founder_role = ctx.guild.get_role(414822833873747984)
            delegate_role = ctx.guild.get_role(622961669634785302)

            if str(rgovernor) == str(nation):
                status = "founder"
            if str(rdelegate) == str(nation):
                status = "delegate"
                if status == "founder":
                    status = "founder+delegate"
            if str(rgovernor) != str(nation) and str(rdelegate) != str(nation):
                print(rgovernor == nation)
                status = "resident"

            await self.bot.execute(
                "INSERT INTO nsl_table (discord_id, nation, status) VALUES ($1, $2, $3)",
                ctx.author.id,
                nation,
                status,
            )
            if "founder" in status:
                await ctx.author.add_roles(founder_role, reason="Verified via NSV")
            if "delegate" in status:
                await ctx.author.add_roles(delegate_role, reason="Verified via NSV")
            if "resident" in status:
                console = ctx.guild.get_channel(626654671167160320)
                await console.send(f"Non-Founder/Delegate joined: {ctx.author.mention}")
            await ctx.author.send(welcome_message)
        else:
            wa = root.find("UNSTATUS").text
            status = None
            if settings[0]["region"] and len(settings[0]["region"].split(",")) > 1:
                set_region = settings[0]["region"].split(",")
                set_region = [x.strip() for x in set_region]
            else:
                set_region = [settings[0]["region"].strip() if settings[0]["region"] else None]
            if set_region:
                if region in set_region:
                    if "WA" in wa:
                        status = "wa-resident"
                    else:
                        status = "resident"
                else:
                    status = "guest"
                await self.bot.execute(
                    "INSERT INTO nsv_table (discord_id, nation, guild_id, status) VALUES ($1, $2, $3, $4)",
                    ctx.author.id,
                    nation,
                    ctx.guild.id,
                    status,
                )
                verified_role = ctx.guild.get_role(settings[0]["verified_role"])
                if status == "guest":
                    guest_role = ctx.guild.get_role(settings[0]["guest_role"])
                    if not guest_role:
                        if not verified_role:
                            pass
                        await ctx.author.add_roles(
                            verified_role, reason="Verified via NSV."
                        )
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
                status = "verified"
                await self.bot.execute(
                    "INSERT INTO nsv_table (discord_id, nation, guild_id, status) VALUES ($1, $2, $3, $4)",
                    ctx.author.id,
                    nation,
                    ctx.guild.id,
                    status,
                )
                verified = ctx.guild.get_role(settings[0]["verified_role"])
                await ctx.author.add_roles(verified, reason="Verified via NSV.")
                await ctx.author.send(welcome_message)

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
        await ctx.defer(ephemeral=True)
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
            try:
                await self.auth_flow(ctx, str(msg.clean_content).lower().replace(" ", "_"))
            except discord.Forbidden:
                await ctx.send("I can't DM you! Please make sure that your DMs are open. Failing to do so will result "
                               "in the process erroring out.")

    @verify.error
    async def verify_error(self, ctx: commands.Context, error: Exception):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send("You're on cooldown! Please wait 60 seconds before trying again.")
        else:
            raise error

    @commands.guild_only()
    @commands.hybrid_command(with_app_command=True)
    async def drop(self, ctx: commands.Context):
        """
        Drops your nation for the server.
        """
        if ctx.guild.id == 414822188273762306:
            listof = await self.bot.fetch("SELECT nation FROM nsl_table WHERE discord_id = $1", ctx.author.id)
            if listof:
                nlist = [record["nation"] for record in listof]
                embed = discord.Embed(
                    title="Which nation would you like to drop?",
                    description="Only the first twenty-five nations that you have verified are shown.",
                    color=discord.Color.blurple(),
                )
                m = await ctx.send(embed=embed, ephemeral=True)
                v = DropView(self.bot, nlist, m)
                await m.edit(view=v)
        else:
            await self.bot.execute(
                "DELETE FROM nsv_table WHERE discord_id = $1 AND guild_id = $2",
                ctx.author.id,
                ctx.guild.id,
            )
            await ctx.send("Done.")


async def setup(bot: Bloo):
    await bot.add_cog(NSV(bot))
