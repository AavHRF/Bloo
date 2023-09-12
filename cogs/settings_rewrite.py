import discord
import asyncpg
from discord.ext import commands
from discord import app_commands
from framework.bot import Bloo
from typing import List, Optional


class Prompt(discord.ui.Modal, title="Bloo Configuration"):

    def __init__(self, bot: Bloo, mode: str, current_settings: Optional[List[asyncpg.Record]] = None):
        super().__init__()
        self.bot = bot
        self.mode = mode
        self.list_settings = current_settings if current_settings else None
        self.internal_settings = current_settings[0] if current_settings else None

        if mode.lower() == "region":
            self.add_item(
                discord.ui.TextInput(
                    label="Region Name",
                    placeholder="Enter your region here. (Leave blank to clear)",
                    max_length=50,
                )
            )
        elif mode.lower() == "welcome":
            self.add_item(
                discord.ui.TextInput(
                    label="Welcome Message",
                    placeholder="Enter your welcome message here. (Leave blank to clear) Max length is 750 characters.",
                    max_length=750,
                    style=discord.TextStyle.paragraph,
                )
            )

    async def on_submit(self, interaction: discord.Interaction):
        if self.mode == "region":
            if self.children[0].value:
                if self.internal_settings:
                    await self.bot.execute(
                        "UPDATE nsv_settings SET region = $1 WHERE guild_id = $2",
                        self.children[0].value,
                        interaction.guild.id,
                    )
                else:
                    await self.bot.execute(
                        "INSERT INTO nsv_settings (guild_id, region) VALUES ($1, $2)",
                        interaction.guild.id,
                        self.children[0].value,
                    )
            else:
                if self.internal_settings:
                    await self.bot.execute(
                        "UPDATE nsv_settings SET region = $1 WHERE guild_id = $2",
                        None,
                        interaction.guild.id,
                    )
                else:
                    pass  # Why would we do anything here?
            embed = interaction.message.embeds[0]
            embed.set_field_at(
                1,
                name="Region",
                value=self.children[0].value if self.children[0].value else "None",
            )
            await interaction.response.edit_message(embed=embed, view=VerificationView(self.bot, embed, self.list_settings))
        elif self.mode == "welcome":
            if self.children[0].value:
                if self.internal_settings:
                    await self.bot.execute(
                        "UPDATE welcome_settings SET message = $1 WHERE guild_id = $2",
                        self.children[0].value,
                        interaction.guild.id,
                    )
                else:
                    await self.bot.execute(
                        "INSERT INTO welcome_settings (guild_id, message) VALUES ($1, $2)",
                        interaction.guild.id,
                        self.children[0].value,
                    )
            else:
                if self.internal_settings:
                    await self.bot.execute(
                        "UPDATE welcome_settings SET message = $1 WHERE guild_id = $2",
                        None,
                        interaction.guild.id,
                    )
                else:
                    pass
            await interaction.response.send_message(
                "Your settings have been updated!",
                ephemeral=True
            )


class NSVRoleView(discord.ui.View):
    def __init__(self, bot: Bloo, current_settings: Optional[List[asyncpg.Record]] = None):
        super().__init__()
        self.bot = bot
        self.internal_settings = current_settings[0] if current_settings else None
        self.list_settings = current_settings if current_settings else None

    @discord.ui.select(cls=discord.ui.RoleSelect, placeholder="Verified Role", row=0)
    async def verified(
            self, interaction: discord.Interaction, select: discord.ui.Select
    ):
        await interaction.response.defer()

    @discord.ui.select(cls=discord.ui.RoleSelect, placeholder="Guest Role", row=1)
    async def guest(self, interaction: discord.Interaction, select: discord.ui.Select):
        await interaction.response.defer()

    @discord.ui.select(cls=discord.ui.RoleSelect, placeholder="Resident Role", row=2)
    async def resident(
            self, interaction: discord.Interaction, select: discord.ui.Select
    ):
        await interaction.response.defer()

    @discord.ui.select(cls=discord.ui.RoleSelect, placeholder="WA Resident Role", row=3)
    async def wa_resident(
            self, interaction: discord.Interaction, select: discord.ui.Select
    ):
        await interaction.response.defer()

    @discord.ui.button(
        label="Save",
        style=discord.ButtonStyle.blurple,
        custom_id="save_roles",
    )
    async def save_roles(
            self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        for child in self.children:
            child.disabled = True
        self.go_back.disabled = False
        try:
            if self.guest.values:
                guest = self.guest.values[0].id
            else:
                if self.internal_settings:
                    guest = self.internal_settings["guest_role"]
                else:
                    guest = 0
        except IndexError:
            guest = 0
        try:
            if self.resident.values:
                resident = self.resident.values[0].id
            else:
                if self.internal_settings:
                    resident = self.internal_settings["resident_role"]
                else:
                    resident = 0
        except IndexError:
            resident = 0
        try:
            if self.wa_resident.values:
                wa_resident = self.wa_resident.values[0].id
            else:
                if self.internal_settings:
                    wa_resident = self.internal_settings["wa_resident_role"]
                else:
                    wa_resident = 0
        except IndexError:
            wa_resident = 0
        try:
            if self.verified.values:
                verified = self.verified.values[0].id
            else:
                if self.internal_settings:
                    verified = self.internal_settings["verified_role"]
                else:
                    verified = 0
        except IndexError:
            verified = 0

        if not self.internal_settings:
            await self.bot.execute(
                "INSERT INTO nsv_settings (guild_id, guest_role, resident_role, wa_resident_role, verified_role) VALUES ($1, $2, $3, $4, $5)",
                interaction.guild.id,
                guest,
                resident,
                wa_resident,
                verified,
            )
            self.list_settings = await self.bot.fetch(
                "SELECT * FROM nsv_settings WHERE guild_id = $1", interaction.guild.id
            )
            self.internal_settings = self.list_settings[0]
        else:
            await self.bot.execute(
                "UPDATE nsv_settings SET guest_role = $1, resident_role = $2, wa_resident_role = $3, verified_role = $4 WHERE guild_id = $5",
                guest,
                resident,
                wa_resident,
                verified,
                interaction.guild.id,
            )
            self.list_settings = await self.bot.fetch(
                "SELECT * FROM nsv_settings WHERE guild_id = $1", interaction.guild.id
            )
            self.internal_settings = self.list_settings[0]
        embed = interaction.message.embeds[0]
        embed.set_field_at(
            2,
            name="Verified Role",
            value=interaction.guild.get_role(
                self.internal_settings["verified_role"]
            ).mention if self.internal_settings["verified_role"] != 0 else "None"
        )
        embed.set_field_at(
            3,
            name="Guest Role",
            value=interaction.guild.get_role(
                self.internal_settings["guest_role"]
            ).mention if self.internal_settings["guest_role"] != 0 else "None"
        )
        embed.set_field_at(
            4,
            name="Resident Role",
            value=interaction.guild.get_role(
                self.internal_settings["resident_role"]
            ).mention if self.internal_settings["resident_role"] != 0 else "None"
        )
        embed.set_field_at(
            5,
            name="WA Resident Role",
            value=interaction.guild.get_role(
                self.internal_settings["wa_resident_role"]
            ).mention if self.internal_settings["wa_resident_role"] != 0 else "None"
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(
        label="Cancel",
        style=discord.ButtonStyle.danger,
        custom_id="cancel_roles",
    )
    async def cancel_roles(
            self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        for child in self.children:
            child.disabled = True
        self.go_back.disabled = False
        await interaction.response.edit_message(view=self)

    @discord.ui.button(
        label="Go Back",
        style=discord.ButtonStyle.secondary,
        custom_id="go_back",
    )
    async def go_back(
            self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.edit_message(
            view=VerificationView(self.bot, interaction.message.embeds[0], self.list_settings))


class VerificationView(discord.ui.View):
    def __init__(
            self,
            bot: Bloo,
            embed: discord.Embed,
            current_settings: Optional[List[asyncpg.Record]] = None,
    ):
        super().__init__()
        self.bot = bot
        self.embed = embed
        self.internal_settings = current_settings[0] if current_settings else None
        self.list_settings = current_settings if current_settings else None

    @discord.ui.button(
        label="Enable/Disable Verification",
        style=discord.ButtonStyle.danger,
        custom_id="verification_toggle",
        emoji="🎛️",
    )
    async def verification_toggle(
            self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if self.internal_settings:
            await self.bot.execute(
                "UPDATE nsv_settings SET force_verification = $1 WHERE guild_id = $2",
                not self.internal_settings["force_verification"],
                interaction.guild.id,
            )
            self.list_settings = await self.bot.fetch(
                "SELECT * FROM nsv_settings WHERE guild_id = $1", interaction.guild.id
            )
            self.internal_settings = self.list_settings[0]
            self.embed.set_field_at(
                0,
                name="Forced Verification Status",
                value="Enabled"
                if self.internal_settings["force_verification"]
                else "Disabled",
            )
            await interaction.response.edit_message(embed=self.embed, view=self)

        else:
            await interaction.response.send_message(
                "You need to set up your role settings first!",
                ephemeral=True,
            )

    @discord.ui.button(
        label="Set Verification Message",
        style=discord.ButtonStyle.blurple,
        custom_id="verification_message",
        emoji="✉️",
    )
    async def verification_message(
            self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        pass

    @discord.ui.button(
        label="Set Roles",
        style=discord.ButtonStyle.blurple,
        custom_id="verification_roles",
        emoji="👥",
    )
    async def verification_roles(
            self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.edit_message(view=NSVRoleView(self.bot, self.list_settings))

    @discord.ui.button(
        label="Set Region",
        style=discord.ButtonStyle.blurple,
        custom_id="verification_region",
        emoji="🌎",
    )
    async def verification_region(
            self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.send_modal(Prompt(self.bot, "region", self.list_settings))


class SettingsView(discord.ui.View):
    def __init__(self, bot: Bloo, embed: discord.Embed):
        super().__init__()
        self.bot = bot

    @discord.ui.button(
        label="Verification Settings",
        style=discord.ButtonStyle.blurple,
        custom_id="verification_settings",
        emoji="✅",
    )
    async def verification_settings(
            self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.defer(
            ephemeral=True
        )  # Defer the response in case the database locks up
        nsv_settings = await self.bot.fetch(
            "SELECT * FROM nsv_settings WHERE guild_id = $1", interaction.guild.id
        )
        if not nsv_settings:
            embed = discord.Embed(
                title=":white_check_mark: Verification Settings",
                description="You seem to have no settings configured! Oh dear! Use the buttons below to get started.",
            )
            await interaction.followup.edit_message(
                message_id=interaction.message.id,
                embed=embed,
                view=VerificationView(self.bot, embed, nsv_settings),
            )
        else:
            embed = discord.Embed(
                title=":white_check_mark: Verification Settings",
                description="Configure your verification settings here.",
            )
            embed.add_field(
                name="Forced Verification Status",
                value="Enabled"
                if nsv_settings[0]["force_verification"]
                else "Disabled",
            )
            embed.add_field(
                name="Region",
                value=nsv_settings[0]["region"].replace("_", " ").title(),
            )
            embed.add_field(
                name="Verified Role",
                value=interaction.guild.get_role(
                    nsv_settings[0]["verified_role"]
                ).mention
                if nsv_settings[0]["verified_role"] != 0
                else "None",
            )
            embed.add_field(
                name="Guest Role",
                value=interaction.guild.get_role(nsv_settings[0]["guest_role"]).mention
                if nsv_settings[0]["guest_role"] != 0
                else "None",
            )
            embed.add_field(
                name="Resident Role",
                value=interaction.guild.get_role(
                    nsv_settings[0]["resident_role"]
                ).mention
                if nsv_settings[0]["resident_role"] != 0
                else "None",
            )
            embed.add_field(
                name="WA Resident Role",
                value=interaction.guild.get_role(
                    nsv_settings[0]["wa_resident_role"]
                ).mention
                if nsv_settings[0]["wa_resident_role"] != 0
                else "None",
            )

            await interaction.followup.edit_message(
                message_id=interaction.message.id,
                embed=embed,
                view=VerificationView(self.bot, embed, nsv_settings),
            )
        pass

    @discord.ui.button(
        label="Guild Settings",
        style=discord.ButtonStyle.blurple,
        custom_id="guild_settings",
        emoji="⚙️",
    )
    async def guild_settings(
            self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        guild_settings = await self.bot.fetch(
            "SELECT * FROM guild_settings WHERE guild_id = $1", interaction.guild.id
        )
        pass

    @discord.ui.button(
        label="Welcome Settings",
        style=discord.ButtonStyle.blurple,
        custom_id="welcome_settings",
        emoji="👋",
    )
    async def welcome_settings(
            self, interaction: discord.Interaction, button: discord.ui.Button
    ):
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
            name=":white_check_mark: Verification Settings",
            value="Change settings for the Verification module.",
            inline=False,
        )
        embed.add_field(
            name=":gear: Guild Settings",
            value="Change settings for the guild.",
            inline=False,
        )
        embed.add_field(
            name=":wave: Welcome Settings",
            value="Change settings for the Welcome module.",
            inline=False,
        )
        await interaction.response.send_message(
            embed=embed, view=SettingsView(self.bot, embed), ephemeral=True
        )


async def setup(bot: Bloo):
    await bot.add_cog(RewrittenSettings(bot))
