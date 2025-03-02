import discord
from gql import gql

class SubscriptionSync:
    """Handles syncing Discord roles with LLDAP Subscribers and Lifetime groups."""
    
    def __init__(self, bot, user_manager, subscriber_role_name, subscribers_group_id, lifetime_role_name, lifetime_group_id):
        self.bot = bot
        self.user_manager = user_manager
        self.subscriber_role_name = subscriber_role_name
        self.subscribers_group_id = subscribers_group_id
        self.lifetime_role_name = lifetime_role_name
        self.lifetime_group_id = lifetime_group_id

    @staticmethod
    def get_attribute_value(attributes, name):
        """Extracts attribute value by name from LLDAP user attributes."""
        for attr in attributes:
            if attr['name'] == name:
                return attr['value'][0] if attr['value'] else None
        return None

    async def fetch_ldap_users_in_group(self, group_id):
        """Fetches all users in a specified LLDAP group."""
        query = gql("""
        query GetGroupDetails($id: Int!) {
            group(groupId: $id) {
                users {
                    id
                    displayName
                    attributes {
                        name
                        value
                    }
                }
            }
        }
        """)
        result = await self.user_manager.graphql_client.execute_query(query, {"id": group_id})

        ldap_users = {}
        if result.get("group") and result["group"].get("users"):
            for user in result["group"]["users"]:
                discord_id = self.get_attribute_value(user["attributes"], "discordid")
                if discord_id:
                    ldap_users[discord_id] = user
        return ldap_users

    async def sync(self):
        """Syncs Discord Subscribers and Lifetime roles with LLDAP group membership."""
        guild = self.bot.guilds[0]  # Assuming bot is only in one server
        subscriber_role = discord.utils.get(guild.roles, name=self.subscriber_role_name)
        lifetime_role = discord.utils.get(guild.roles, name=self.lifetime_role_name)

        if not subscriber_role:
            print("⚠️ Subscriber role not found!")
        if not lifetime_role:
            print("⚠️ Lifetime role not found!")
        if not (subscriber_role or lifetime_role):
            return

        # Fetch LDAP users for both groups
        print("🔍 Fetching users from LLDAP...")
        subscriber_ldap_users = await self.fetch_ldap_users_in_group(self.subscribers_group_id)
        lifetime_ldap_users = await self.fetch_ldap_users_in_group(self.lifetime_group_id)
        print(f"📜 Found {len(subscriber_ldap_users)} LLDAP users in the 'Subscribers' group.")
        print(f"📜 Found {len(lifetime_ldap_users)} LLDAP users in the 'Lifetime' group.")

        # Get Discord users with each role, mapping ID to username
        discord_subscribers = {str(member.id): member.name for member in guild.members if subscriber_role and subscriber_role in member.roles}
        discord_lifetime = {str(member.id): member.name for member in guild.members if lifetime_role and lifetime_role in member.roles}
        print(f"🔍 Found {len(discord_subscribers)} Discord users with the 'Subscribers' role.")
        print(f"🔍 Found {len(discord_lifetime)} Discord users with the 'Lifetime' role.")

        # Sync Subscribers group
        if subscriber_role:
            # Remove users from LLDAP Subscribers if they don't have the Discord role
            removed_from_subscribers = []
            for discord_id, user in subscriber_ldap_users.items():
                if discord_id not in discord_subscribers:
                    print(f"🚨 User {user['displayName']} ({discord_id}) is in LLDAP Subscribers but does NOT have the Discord role! Removing from Subscribers group...")
                    await self.user_manager.remove_from_subscribers_group(user["id"])
                    removed_from_subscribers.append(user["id"])

            # Add users to LLDAP Subscribers if they have the Discord role but are not in the group
            added_to_subscribers = []
            for discord_id, username in discord_subscribers.items():
                if discord_id not in subscriber_ldap_users:
                    print(f"🟢 User {username} ({discord_id}) has the Discord Subscriber role but is NOT in LLDAP! Adding to Subscribers group...")
                    lldap_user_id = await self.user_manager.get_user_by_discord_id(discord_id)
                    if lldap_user_id:
                        await self.user_manager.add_to_subscribers_group(lldap_user_id)
                        added_to_subscribers.append(discord_id)

        # Sync Lifetime group
        if lifetime_role:
            # Remove users from LLDAP Lifetime if they don't have the Discord role
            removed_from_lifetime = []
            for discord_id, user in lifetime_ldap_users.items():
                if discord_id not in discord_lifetime:
                    print(f"🚨 User {user['displayName']} ({discord_id}) is in LLDAP Lifetime but does NOT have the Discord role! Removing from Lifetime group...")
                    await self.user_manager.remove_from_group(user["id"], self.lifetime_group_id)
                    removed_from_lifetime.append(user["id"])

            # Add users to LLDAP Lifetime if they have the Discord role but are not in the group
            added_to_lifetime = []
            for discord_id, username in discord_lifetime.items():
                if discord_id not in lifetime_ldap_users:
                    print(f"🟢 User {username} ({discord_id}) has the Discord Lifetime role but is NOT in LLDAP! Adding to Lifetime group...")
                    lldap_user_id = await self.user_manager.get_user_by_discord_id(discord_id)
                    if lldap_user_id:
                        await self.user_manager.add_to_group(lldap_user_id, self.lifetime_group_id)
                        added_to_lifetime.append(discord_id)

        print(f"🔄 Sync complete: "
              f"Subscribers - Removed {len(removed_from_subscribers)} users, Added {len(added_to_subscribers)} users; "
              f"Lifetime - Removed {len(removed_from_lifetime)} users, Added {len(added_to_lifetime)} users.")