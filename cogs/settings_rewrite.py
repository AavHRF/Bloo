import discord
import asyncpg
from discord.ext import commands
from discord import app_commands
from framework.bot import Bloo
from typing import List


class VerificationView(discord.ui.View):

    def __init__(self, bot: Bloo, current_settings: List[asyncpg.Record]):
        super().__init__()
        self.bot = bot
        self.current_settings = current_settings

    @discord.ui.button(
        label="Enable/Disable Verification",
        style=discord.ButtonStyle.danger,
        custom_id="verification_toggle",
        emoji=":white_check_mark:",
    )
    async def verification_toggle(self, interaction: discord.Interaction, button: discord.ui.Button):
        pass


class SettingsView(discord.ui.View):

    def __init__(self, bot: Bloo):
        super().__init__()
        self.bot = bot

    @discord.ui.button(
        label="Verification Settings",
        style=discord.ButtonStyle.blurple,
        custom_id="verification_settings",
        # emoji=discord.PartialEmoji.from_str("white_check_mark"),
    )
    async def verification_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)  # Defer the response in case the database locks up
        nsv_settings = await self.bot.fetch(
            "SELECT * FROM nsv_settings WHERE guild_id = $1", interaction.guild.id
        )
        if not nsv_settings:
            embed = discord.Embed(
                title="Verification Settings",
                description="You seem to have no settings configured! Oh dear! Use the buttons below to get started.",
            )
            await interaction.response.followup.edit_message(embed=embed, view=VerificationView(self.bot, nsv_settings))
        else:
            embed = discord.Embed(
                title="Verification Settings",
                description="Configure your verification settings here.",
            )
            await interaction.response.followup.edit_message(embed=embed, view=VerificationView(self.bot, nsv_settings))
        pass

    @discord.ui.button(
        label="Guild Settings",
        style=discord.ButtonStyle.blurple,
        custom_id="guild_settings",
        # emoji=discord.PartialEmoji.from_str("gear"),
    )
    async def guild_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_settings = await self.bot.fetch(
            "SELECT * FROM guild_settings WHERE guild_id = $1", interaction.guild.id
        )
        pass

    @discord.ui.button(
        label="Welcome Settings",
        style=discord.ButtonStyle.blurple,
        custom_id="welcome_settings",
        # emoji=discord.PartialEmoji.from_str("wave"),
    )
    async def welcome_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        welcome_settings = await self.bot.fetch(
            "SELECT * FROM welcome_settings WHERE guild_id = $1", interaction.guild.id
        )
        pass


class RewrittenSettings(commands.Cog):

    def __init__(self, bot: Bloo):
        self.bot = bot

    @app_commands.guilds(1034294542247133194)
    @app_commands.command(
        name="rwsettings",
        description="Change settings for the bot",
    )
    async def settings(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="Settings",
            description="Welcome to Bloo! Configure your settings here.",
            color=discord.Color.random(),
        )
        embed.add_field(
            name="Verification Settings",
            value="Change settings for the Verification module.",
            inline=False,
        )
        embed.add_field(
            name="Guild Settings",
            value="Change settings for the guild.",
            inline=False,
        )
        embed.add_field(
            name="Welcome Settings",
            value="Change settings for the Welcome module.",
            inline=False,
        )
        await interaction.response.send_message(embed=embed, view=SettingsView(self.bot), ephemeral=True)


async def setup(bot: Bloo):
    await bot.add_cog(RewrittenSettings(bot))