import discord
from discord.ext import commands
from discord import app_commands
from framework.bot import Bloo


class RegionModal(discord.ui.Modal, title="Set Region"):

    name = discord.ui.TextInput(
        label="Region Name",
        placeholder="The North Pacific",
        min_length=1,
        max_length=50,
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message("Submitted!", ephemeral=True)
        # noinspection PyTypeChecker
        bot: Bloo = interaction.client
        await bot.execute(
            "INSERT INTO nsv_settings (guild_id, region) VALUES ($1, $2) ON CONFLICT (guild_id) DO UPDATE SET region = $2",
            interaction.guild.id,
            self.name.value.lower().replace(" ", "_"),
        )


class SettingsView(discord.ui.View):
    def __init__(self, m: discord.Message):
        super().__init__(timeout=300)
        self.message = m

    @discord.ui.button(label="Save", style=discord.ButtonStyle.green, row=4)
    async def save(self, interaction: discord.Interaction, button: discord.ui.Button):
        # noinspection PyTypeChecker
        bot: Bloo = interaction.client
        # Fail if not all the selects have a value
        if (
            not self.v.values
            or not self.g.values
            or not self.r.values
            or not self.wr.values
        ):
            await interaction.response.send_message(
                "Please select a role in all categories!", ephemeral=True
            )
            return
        await bot.execute(
            "INSERT INTO nsv_settings (guild_id, verified_role, guest_role, resident_role, wa_resident_role) VALUES ($1, $2, $3, $4, $5) ON CONFLICT (guild_id) DO UPDATE SET verified_role = $2, guest_role = $3, resident_role = $4, wa_resident_role = $5",
            interaction.guild.id,
            self.v.values[0].id,
            self.g.values[0].id,
            self.r.values[0].id,
            self.wr.values[0].id,
        )
        await interaction.response.send_message("Settings saved!", ephemeral=True)
        for child in self.children:
            child.disabled = True
        await self.message.edit(view=self)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, row=4)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        for child in self.children:
            child.disabled = True
        await self.message.edit(view=self)
        await interaction.response.send_message("Cancelled!", ephemeral=True)
        button.disabled = True
        self.stop()

    @discord.ui.button(label="Set Region", style=discord.ButtonStyle.blurple, row=4)
    async def set_region(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.send_modal(RegionModal())

    @discord.ui.select(cls=discord.ui.RoleSelect, placeholder="Verified Role", row=0)
    async def v(self, interaction: discord.Interaction, select: discord.ui.Select):
        await interaction.response.defer()

    @discord.ui.select(cls=discord.ui.RoleSelect, placeholder="Guest Role", row=1)
    async def g(self, interaction: discord.Interaction, select: discord.ui.Select):
        await interaction.response.defer()

    @discord.ui.select(cls=discord.ui.RoleSelect, placeholder="Resident Role", row=2)
    async def r(self, interaction: discord.Interaction, select: discord.ui.Select):
        await interaction.response.defer()

    @discord.ui.select(cls=discord.ui.RoleSelect, placeholder="WA Resident Role", row=3)
    async def wr(self, interaction: discord.Interaction, select: discord.ui.Select):
        await interaction.response.defer()


class Settings(commands.Cog):
    def __init__(self, bot: Bloo):
        self.bot = bot

    @app_commands.command()
    async def settings(self, interaction: discord.Interaction):
        """Configure NSV settings for the server"""
        await interaction.response.defer()
        embed = discord.Embed(
            title="Settings",
            description="This menu lets you set the roles for the bot to use, along with the region your server is for.",
            color=discord.Color.blurple(),
        )
        menu = await interaction.followup.send(embed=embed, ephemeral=True)
        await menu.edit(view=SettingsView(menu))


async def setup(bot: Bloo):
    await bot.add_cog(Settings(bot))
