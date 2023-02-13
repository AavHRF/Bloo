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


class VerificationMessageModal(discord.ui.Modal, title="Set Verification Message"):
    message = discord.ui.TextInput(
        label="Verification Message",
        placeholder="Welcome to The North Pacific!",
        min_length=1,
        max_length=2000,
        style=discord.TextStyle.long,
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message("Submitted!", ephemeral=True)
        # noinspection PyTypeChecker
        bot: Bloo = interaction.client
        await bot.execute(
            "INSERT INTO nsv_settings (guild_id, welcome_message) VALUES ($1, $2) ON CONFLICT (guild_id) DO UPDATE SET welcome_message = $2",
            interaction.guild.id,
            self.message.value,
        )


class WelcomeMessageModal(discord.ui.Modal, title="Set Welcome Message"):
    message = discord.ui.TextInput(
        label="Welcome Message",
        placeholder="Welcome to The North Pacific!",
        min_length=1,
        max_length=500,
        style=discord.TextStyle.long,
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message("Submitted!", ephemeral=True)
        # noinspection PyTypeChecker
        bot: Bloo = interaction.client
        await bot.execute(
            "INSERT INTO welcome_settings (guild_id, embed_message) VALUES ($1, $2) ON CONFLICT (guild_id) DO UPDATE SET embed_message = $2",
            interaction.guild.id,
            self.message.value,
        )


class SettingsView(discord.ui.View):
    def __init__(self, m: discord.Message):
        super().__init__(timeout=300)
        self.message = m

    @discord.ui.button(label="Save", style=discord.ButtonStyle.green, row=4)
    async def save(self, interaction: discord.Interaction, button: discord.ui.Button):
        # noinspection PyTypeChecker
        bot: Bloo = interaction.client
        await bot.execute(
            "INSERT INTO nsv_settings (guild_id, verified_role, guest_role, resident_role, wa_resident_role, force_verification) VALUES ($1, $2, $3, $4, $5, $6) ON CONFLICT (guild_id) DO UPDATE SET verified_role = $2, guest_role = $3, resident_role = $4, wa_resident_role = $5",
            interaction.guild.id,
            self.v.values[0].id if self.v.values else 0,
            self.g.values[0].id if self.g.values else 0,
            self.r.values[0].id if self.r.values else 0,
            self.wr.values[0].id if self.wr.values else 0,
            False
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

    @discord.ui.button(
        label="Set Verification DM Message", style=discord.ButtonStyle.blurple, row=4
    )
    async def set_welcome_message(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.send_modal(VerificationMessageModal())

    @discord.ui.button(
        label="Enable/Disable Forced Verification", style=discord.ButtonStyle.red, row=4
    )
    async def enable_verification(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        # noinspection PyTypeChecker
        bot: Bloo = interaction.client
        current_state = await bot.fetchval(
            "SELECT force_verification FROM nsv_settings WHERE guild_id = $1",
            interaction.guild.id,
        )
        if current_state:
            state = current_state[0]["force_verification"]
        else:
            state = False
        await bot.execute(
            "INSERT INTO nsv_settings (guild_id, force_verification) VALUES ($1, $2) ON CONFLICT (guild_id) DO UPDATE SET force_verification = $2",
            interaction.guild.id,
            not state,
        )
        if not state:
            await interaction.response.send_message("Enabled!", ephemeral=True)
        else:
            await interaction.response.send_message("Disabled!", ephemeral=True)
        button.disabled = True
        await self.message.edit(view=self)

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


class WelcomeView(discord.ui.View):
    def __init__(self, m: discord.Message):
        self.message = m
        super().__init__(timeout=300)

    @discord.ui.select(
        cls=discord.ui.ChannelSelect,
        placeholder="Set Welcome Channel",
        row=0,
        channel_types=[discord.ChannelType.text],
    )
    async def wc(self, interaction: discord.Interaction, select: discord.ui.Select):
        await interaction.response.defer()

    @discord.ui.button(
        label="Enable/disable leave/join messages",
        style=discord.ButtonStyle.blurple,
        row=1,
    )
    async def edljm(self, interaction: discord.Interaction, button: discord.ui.Button):
        # noinspection PyTypeChecker
        bot: Bloo = interaction.client
        await interaction.response.defer()
        current_state = await bot.fetch(
            "SELECT welcome_enabled FROM welcome_settings WHERE guild_id = $1",
            interaction.guild.id,
        )
        if current_state:
            current_state = current_state[0]["welcome_enabled"]
        else:
            current_state = False
        await bot.execute(
            "INSERT INTO welcome_settings (guild_id, welcome_enabled) VALUES ($1, $2) ON CONFLICT (guild_id) DO UPDATE SET welcome_enabled = $2",
            interaction.guild.id,
            not current_state,
        )
        await interaction.followup.send(
            f"Welcome messages are now {'enabled' if not current_state else 'disabled'}",
            ephemeral=True,
        )

    @discord.ui.button(
        label="Enable/disable ping on join",
        style=discord.ButtonStyle.blurple,
        row=1,
    )
    async def edpoj(self, interaction: discord.Interaction, button: discord.ui.Button):
        # noinspection PyTypeChecker
        bot: Bloo = interaction.client
        await interaction.response.defer()
        current_state = await bot.fetch(
            "SELECT ping_on_join FROM welcome_settings WHERE guild_id = $1",
            interaction.guild.id,
        )
        if current_state:
            current_state = current_state[0]["ping_on_join"]
        else:
            current_state = False
        await bot.execute(
            "INSERT INTO welcome_settings (guild_id, ping_on_join) VALUES ($1, $2) ON CONFLICT (guild_id) DO UPDATE SET ping_on_join = $2",
            interaction.guild.id,
            not current_state,
        )
        await interaction.followup.send(
            f"Ping on join is now {'enabled' if not current_state else 'disabled'}",
            ephemeral=True,
        )

    @discord.ui.button(
        label="Set join message",
        style=discord.ButtonStyle.blurple,
        row=1,
    )
    async def set_join_message(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.send_modal(WelcomeMessageModal())

    @discord.ui.button(label="Save", style=discord.ButtonStyle.green, row=2)
    async def save(self, interaction: discord.Interaction, button: discord.ui.Button):
        # noinspection PyTypeChecker
        bot: Bloo = interaction.client
        await bot.execute(
            "INSERT INTO welcome_settings (guild_id, welcome_channel) VALUES ($1, $2) ON CONFLICT (guild_id) DO UPDATE SET welcome_channel = $2",
            interaction.guild.id,
            self.wc.values[0].id if self.wc.values else 0,
        )
        await interaction.response.send_message("Settings saved!", ephemeral=True)
        for child in self.children:
            child.disabled = True
        await self.message.edit(view=self)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, row=2)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        for child in self.children:
            child.disabled = True
        await self.message.edit(view=self)
        await interaction.response.send_message("Cancelled!", ephemeral=True)
        button.disabled = True
        self.stop()


class Settings(commands.Cog):
    def __init__(self, bot: Bloo):
        self.bot = bot

    @app_commands.command()
    @app_commands.default_permissions(manage_guild=True)
    async def settings(self, interaction: discord.Interaction):
        """Configure NSV settings for the server"""
        await interaction.response.defer(ephemeral=True)
        embed = discord.Embed(
            title="Settings",
            description="This menu lets you set the roles for the bot to use, along with the region your server is for.",
            color=discord.Color.blurple(),
        )
        menu = await interaction.followup.send(embed=embed, ephemeral=True)
        await menu.edit(view=SettingsView(menu))

    @app_commands.command()
    @app_commands.default_permissions(manage_guild=True)
    async def welcome(self, interaction: discord.Interaction):
        """Configure the welcome message for the server"""
        await interaction.response.defer(ephemeral=True)
        embed = discord.Embed(
            title="Welcome Configuration",
            description="This menu lets you set the welcome message for the server, whether or not embeds are shown "
            "on server join, and the channel to send the welcome message in.\n\nThe welcome message can "
            "contain @mentionables, #channels, and emojis -- however, they must be formatted "
            "appropriately.\n`- Member: <@id number>`\n`- Role: <@&id number>`\n`- Channel: <#id number>`",
            color=discord.Color.blurple(),
        )
        menu = await interaction.followup.send(embed=embed, ephemeral=True)
        await menu.edit(view=WelcomeView(menu))


async def setup(bot: Bloo):
    await bot.add_cog(Settings(bot))
