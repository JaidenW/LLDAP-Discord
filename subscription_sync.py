import discord  # Add this import
from gql import gql

class SubscriptionSync:
    """Handles syncing Discord roles with LLDAP Subscribers group."""
    
    def __init__(self, bot, user_manager, subscriber_role_name, subscribers_group_id):
        self.bot = bot
        self.user_manager = user_manager
        self.subscriber_role_name = subscriber_role_name
        self.subscribers_group_id = subscribers_group_id

    @staticmethod
    def get_attribute_value(attributes, name):
        """Extracts attribute value by name from LLDAP user attributes."""
        for attr in attributes:
            if attr['name'] == name:
                return attr['value'][0] if attr['value'] else None
        return None

    async def fetch_ldap_users_in_group(self):
        """Fetches all users in the LLDAP Subscribers group."""
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
        result = await self.user_manager.graphql_client.execute_query(query, {"id": self.subscribers_group_id})

        ldap_users = {}
        if result.get("group") and result["group"].get("users"):
            for user in result["group"]["users"]:
                discord_id = self.get_attribute_value(user["attributes"], "discordid")
                if discord_id:
                    ldap_users[discord_id] = user
        return ldap_users

    async def sync(self):
        """Syncs Discord Subscribers role with LLDAP group membership."""
        guild = self.bot.guilds[0]  # Assuming bot is only in one server
        role = discord.utils.get(guild.roles, name=self.subscriber_role_name)

        if not role:
            print("⚠️ Subscriber role not found!")
            return

        print("🔍 Fetching users from LLDAP...")
        ldap_users = await self.fetch_ldap_users_in_group()
        print(f"📜 Found {len(ldap_users)} LLDAP users in the 'Subscribers' group.")

        # Get all Discord users with the Subscribers role
        discord_subscribers = {str(member.id) for member in guild.members if role in member.roles}
        print(f"🔍 Found {len(discord_subscribers)} Discord users with the 'Subscribers' role.")

        # Remove users from LLDAP if they don't have the Discord role
        removed_from_ldap = []
        for discord_id, user in ldap_users.items():
            if discord_id not in discord_subscribers:
                print(f"🚨 User {user['displayName']} ({discord_id}) is in LLDAP but does NOT have the Discord role! Removing from LLDAP group...")
                await self.user_manager.remove_from_subscribers_group(user["id"])
                removed_from_ldap.append(user["id"])

        # Add users to LLDAP if they have the Discord role but are not in the group
        added_to_ldap = []
        for discord_id in discord_subscribers:
            if discord_id not in ldap_users:
                print(f"🟢 User {discord_id} has the Discord role but is NOT in LLDAP! Adding to Subscribers group...")
                lldap_user_id = await self.user_manager.get_user_by_discord_id(discord_id)
                if lldap_user_id:
                    await self.user_manager.add_to_subscribers_group(lldap_user_id)
                    added_to_ldap.append(discord_id)

        print(f"🔄 Sync complete: Removed {len(removed_from_ldap)} users, Added {len(added_to_ldap)} users.")