import discord
from discord.ext import tasks
from discord import app_commands

class DiscordBot:
    """Handles Discord bot setup, commands, and background tasks."""
    
    def __init__(self, token, subscriber_role_name, subscriptions_sync, service_name, lifetime_role_name="Subscriber", lifetime_group_id=4):
        intents = discord.Intents.default()
        intents.guilds = True
        intents.members = True
        self.bot = discord.Client(intents=intents)
        self.tree = app_commands.CommandTree(self.bot)
        self.token = token
        self.subscriber_role_name = subscriber_role_name
        self.lifetime_role_name = lifetime_role_name
        self.lifetime_group_id = lifetime_group_id
        self.subscriptions_sync = subscriptions_sync
        self.user_manager = subscriptions_sync.user_manager
        self.lldap_login_url = None
        self.service_name = service_name
        self.public_url = None

    async def start(self, lldap_login_url, public_url):
        """Starts the Discord bot within the existing event loop."""
        self.lldap_login_url = lldap_login_url
        self.public_url = public_url
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

    async def register_command(self, interaction: discord.Interaction, email: str, username: str = None):
        """Handles the /register command to create a new LLDAP user with appropriate group assignment."""
        guild = interaction.guild
        member = guild.get_member(interaction.user.id)
        subscriber_role = discord.utils.get(guild.roles, name=self.subscriber_role_name)
        lifetime_role = discord.utils.get(guild.roles, name=self.lifetime_role_name)

        # Check which roles the user has
        has_subscriber = subscriber_role and subscriber_role in member.roles
        has_lifetime = lifetime_role and lifetime_role in member.roles

        if not (has_subscriber or has_lifetime):
            await interaction.response.send_message(
                f"❌ You must have either the **{self.subscriber_role_name}** or **{self.lifetime_role_name}** role to register an account.", ephemeral=True
            )
            return

        # Normalize email and extract user details
        normalized_email = email.lower()
        user_id = str(interaction.user.id)
        # Use provided username if given, otherwise default to Discord username
        chosen_username = username if username else interaction.user.name

        # Validate username (alphanumeric and max 20 characters)
        if not chosen_username or not chosen_username.isalnum() or len(chosen_username) > 20:
            await interaction.response.send_message(
                "❌ Username must be alphanumeric (letters and numbers only) and no longer than 20 characters.", ephemeral=True
            )
            return

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

        # Determine account type message based on roles
        account_type = self.lifetime_role_name if has_lifetime else self.subscriber_role_name
        
        # Create user in LLDAP with appropriate group assignments
        temp_password, error = await self.user_manager.create_user(
            chosen_username, normalized_email, user_id, 
            subscriber_group=has_subscriber, 
            lifetime_group=has_lifetime,
            lifetime_group_id=self.lifetime_group_id
        )

        if temp_password:
            await interaction.response.send_message(
                f":white_check_mark: **__{self.service_name} {account_type} Account Created!__**\n\n"
                f"__**Use this link to log in and change your password:**__ {self.public_url}\n\n"
                f"**Username**: `{chosen_username}`\n"
                f"**Temporary Password**: `{temp_password}`",
                ephemeral=True
            )
        else:
            if "UNIQUE constraint failed" in str(error):
                await interaction.response.send_message(
                    "❌ This username or Discord ID is already in use.", ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"❌ Failed to create an account: {error}", ephemeral=True
                )

    def setup_commands(self):
        """Sets up slash commands for the bot."""
        @self.tree.command(name="register", description="Register a new LLDAP account based on your Discord roles")
        @app_commands.describe(
            email="Your email address",
            username="🔧 Choose your LLDAP username (optional, defaults to Discord username, max 30 chars, alphanumeric)"
        )
        async def register(interaction: discord.Interaction, email: str, username: str = None):
            await self.register_command(interaction, email, username)

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