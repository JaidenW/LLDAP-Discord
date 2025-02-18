import discord
from discord.ext import tasks
from discord import app_commands

class DiscordBot:
    """Handles Discord bot setup, commands, and background tasks."""
    
    def __init__(self, token, subscriber_role_name, subscriptions_sync, service_name):
        intents = discord.Intents.default()
        intents.guilds = True
        intents.members = True
        self.bot = discord.Client(intents=intents)
        self.tree = app_commands.CommandTree(self.bot)
        self.token = token
        self.subscriber_role_name = subscriber_role_name
        self.subscriptions_sync = subscriptions_sync
        self.user_manager = subscriptions_sync.user_manager
        self.lldap_login_url = None  # Set during initialization
        self.service_name = service_name  # Add service_name

    async def start(self, lldap_login_url):
        """Starts the Discord bot within the existing event loop."""
        self.lldap_login_url = lldap_login_url
        self.setup_commands()
        self.bot.event(self.on_ready)
        await self.bot.start(self.token)

    async def on_ready(self):
        """Handles bot startup, syncs commands, and starts background tasks."""
        print(f"✅ {self.bot.user} is online!")
        try:
            synced = await self.tree.sync()
            print(f"Synced {len(synced)} command(s)")
        except Exception as e:
            print(f"Failed to sync commands: {e}")
        self.sync_subscriptions.start()

    @staticmethod
    def is_admin(interaction: discord.Interaction):
        """Checks if the user has admin permissions."""
        return interaction.user.guild_permissions.administrator

    async def register_command(self, interaction: discord.Interaction, email: str):
        """Handles the /register command to create a new LLDAP user."""
        guild = interaction.guild
        member = guild.get_member(interaction.user.id)
        role = discord.utils.get(guild.roles, name=self.subscriber_role_name)

        # Ensure the Subscribers role exists
        if not role:
            await interaction.response.send_message(
                "❌ Error: The Subscribers role does not exist. Please contact an admin.", ephemeral=True
            )
            return

        # Check if the user has the Subscribers role
        if role not in member.roles:
            await interaction.response.send_message(
                f"❌ You must have the **{self.subscriber_role_name}** role to register an account.", ephemeral=True
            )
            return

        # Normalize email and extract user details
        normalized_email = email.lower()
        user_id = str(interaction.user.id)
        display_name = interaction.user.name

        # Check if email is already associated with an LLDAP account
        if await self.user_manager.check_email_exists(normalized_email):
            await interaction.response.send_message(
                "❌ This email is already associated with an account.", ephemeral=True
            )
            return

        # Check if Discord ID is already linked to an LLDAP account
        if await self.user_manager.check_discord_id_exists(user_id):
            await interaction.response.send_message(
                "❌ You have already linked your Discord to an account.", ephemeral=True
            )
            return

        # Create user in LLDAP
        temp_password, error = await self.user_manager.create_user(display_name, normalized_email, user_id)

        if temp_password:
            await interaction.response.send_message(
                f":white_check_mark: **__{self.service_name} Account Created!__**\n\n"
                f"__**Use this link to log in and change your password:**__ {self.lldap_login_url}\n\n"
                f"**Username**: `{display_name}`\n"
                f"**Temporary Password**: `{temp_password}`",
                ephemeral=True
            )
        else:
            # Detect UNIQUE constraint error and provide a better message
            if "UNIQUE constraint failed" in str(error):
                await interaction.response.send_message(
                    "❌ You have already linked your Discord to an account.", ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"❌ Failed to create an account: {error}", ephemeral=True
                )

    def setup_commands(self):
        """Sets up slash commands for the bot."""
        @self.tree.command(name="register", description="Register a new LLDAP account")
        async def register(interaction: discord.Interaction, email: str):
            await self.register_command(interaction, email)

        @self.tree.command(name="sync_subscribers", description="Manually sync Discord subscribers with LLDAP")
        @app_commands.check(self.is_admin)
        async def sync_subscribers(interaction: discord.Interaction):
            await interaction.response.send_message(
                "🔄 **Manually syncing subscribers...**", ephemeral=True
            )
            try:
                await self.subscriptions_sync.sync()
                await interaction.followup.send(
                    "✅ **Subscriber sync completed successfully.**", ephemeral=True
                )
            except Exception as e:
                await interaction.followup.send(
                    f"❌ **Error during subscriber sync:** {e}", ephemeral=True
                )

    @tasks.loop(minutes=10)
    async def sync_subscriptions(self):
        """Background task to sync Discord roles with LLDAP every 10 minutes."""
        await self.subscriptions_sync.sync()