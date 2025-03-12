import random
import string
from gql import gql

class UserManager:
    """Handles user-related operations for LLDAP, including creation and group management."""
    
    def __init__(self, graphql_client, ldap_manager, subscribers_group_id, ldap_base_dn):
        self.graphql_client = graphql_client
        self.ldap_manager = ldap_manager
        self.subscribers_group_id = subscribers_group_id
        self.ldap_base_dn = ldap_base_dn

    @staticmethod
    def generate_temp_password(length=12):
        """Generates a random temporary password."""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

    async def check_email_exists(self, email):
        """Checks if an email is already associated with an LLDAP account."""
        normalized_email = email.lower()
        query = gql("""
        query GetUserByEmail($email: String!) {
            users(filters: { eq: { field: "email", value: $email } }) {
                id
            }
        }
        """)
        result = await self.graphql_client.execute_query(query, {"email": normalized_email})
        return len(result.get("users", [])) > 0

    async def check_discord_id_exists(self, discord_id):
        """Checks if a Discord ID is already linked to an LLDAP account."""
        query = gql("""
        query GetUserByDiscordId($discordid: String!) {
            users(filters: { eq: { field: "discordid", value: $discordid } }) {
                id
            }
        }
        """)
        result = await self.graphql_client.execute_query(query, {"discordid": discord_id})
        return len(result.get("users", [])) > 0

    async def create_user(self, display_name, email, discord_id, subscriber_group=True, lifetime_group=False, lifetime_group_id=None):
        """Creates a new LLDAP user and adds them to appropriate groups based on parameters."""
        temp_password = self.generate_temp_password()
        create_user_mutation = gql("""
        mutation CreateUser($input: CreateUserInput!) {
            createUser(user: $input) {
                id
            }
        }
        """)
        variables = {
            "input": {
                "id": display_name,  # This is now the chosen username
                "displayName": display_name,
                "email": email,
                "attributes": [{"name": "discordid", "value": [discord_id]}]
            }
        }

        try:
            result = await self.graphql_client.execute_mutation(create_user_mutation, variables)
            user_id = result["createUser"]["id"]

            # Set LDAP password
            user_dn = f"uid={user_id},ou=people,{self.ldap_base_dn}"
            if not self.ldap_manager.set_password(user_dn, temp_password):
                return None, "Failed to set LDAP password"

            # Add to groups based on parameters
            if subscriber_group:
                await self.add_to_subscribers_group(user_id)
            if lifetime_group and lifetime_group_id:
                await self.add_to_group(user_id, lifetime_group_id)

            return temp_password, None
        except Exception as e:
            return None, str(e)



    async def remove_from_group(self, user_id, group_id):
        """Removes a user from a specified group in LLDAP."""
        mutation = gql("""
        mutation RemoveUserFromGroup($userId: String!, $groupId: Int!) {
            removeUserFromGroup(userId: $userId, groupId: $groupId) {
                ok
            }
        }
        """)
        await self.graphql_client.execute_mutation(mutation, {"userId": user_id, "groupId": group_id})


    async def add_to_subscribers_group(self, user_id):
        """Adds a user to the Subscribers group in LLDAP."""
        await self.add_to_group(user_id, self.subscribers_group_id)

    async def add_to_group(self, user_id, group_id):
        """Adds a user to a specified group in LLDAP."""
        mutation = gql("""
        mutation AddUserToGroup($userId: String!, $groupId: Int!) {
            addUserToGroup(userId: $userId, groupId: $groupId) {
                ok
            }
        }
        """)
        await self.graphql_client.execute_mutation(mutation, {"userId": user_id, "groupId": group_id})

    async def remove_from_subscribers_group(self, user_id):
        """Removes a user from the Subscribers group in LLDAP."""
        mutation = gql("""
        mutation RemoveUserFromGroup($userId: String!, $groupId: Int!) {
            removeUserFromGroup(userId: $userId, groupId: $groupId) {
                ok
            }
        }
        """)
        await self.graphql_client.execute_mutation(mutation, {"userId": user_id, "groupId": self.subscribers_group_id})

    async def get_user_by_discord_id(self, discord_id):
        """Retrieves an LLDAP user by their Discord ID."""
        query = gql("""
        query GetUserByDiscordId($discordid: String!) {
            users(filters: { eq: { field: "discordid", value: $discordid } }) {
                id
            }
        }
        """)
        result = await self.graphql_client.execute_query(query, {"discordid": discord_id})
        return result["users"][0]["id"] if result.get("users") else None