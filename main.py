import asyncio
from environment_config import EnvironmentConfig
from auth_manager import AuthManager
from graphql_client import GraphQLClient
from ldap_manager import LDAPManager
from user_manager import UserManager
from subscription_sync import SubscriptionSync
from discord_bot import DiscordBot

async def main():
    # Load environment variables
    config = EnvironmentConfig()

    # Extract username from LDAP_BIND_DN
    ldap_username = config.get_ldap_username()

    # Initialize AuthManager for token-based authentication
    auth_manager = AuthManager(config.lldap_login_url, ldap_username, config.ldap_bind_password)
    await auth_manager.initialize()

    # Initialize GraphQL client with AuthManager
    graphql_client = GraphQLClient(config.lldap_login_url, auth_manager)
    await graphql_client.initialize()

    # Initialize LDAP manager
    ldap_manager = LDAPManager(config.ldap_server, config.ldap_bind_dn, config.ldap_bind_password)

    # Initialize user manager
    user_manager = UserManager(graphql_client, ldap_manager, config.subscribers_group_id, config.ldap_base_dn)

    # Initialize subscription sync with Lifetime parameters
    subscriptions_sync = SubscriptionSync(
        None, 
        user_manager, 
        config.subscriber_role_name, 
        config.subscribers_group_id,
        config.lifetime_role_name,  # Add these from config
        config.lifetime_group_id
    )

    # Initialize Discord bot with Lifetime parameters
    bot = DiscordBot(
        config.discord_bot_token, 
        config.subscriber_role_name, 
        subscriptions_sync, 
        config.service_name,
        config.lifetime_role_name,  # Add these from config
        config.lifetime_group_id
    )
    subscriptions_sync.bot = bot.bot  # Set bot instance after initialization

    # Start the bot within the same event loop
    try:
        await bot.start(config.lldap_login_url, config.public_url)
    finally:
        await auth_manager.close()  # Clean up AuthManager session

if __name__ == "__main__":
    loop = asyncio.new_event_loop()  # Create a new event loop explicitly
    asyncio.set_event_loop(loop)  # Set the new loop as the current loop
    try:
        loop.run_until_complete(main())
    finally:
        loop.close()  # Clean up the loop