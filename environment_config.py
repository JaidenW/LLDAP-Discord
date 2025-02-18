import os
from dotenv import load_dotenv

class EnvironmentConfig:
    """Loads and stores environment variables for the application."""
    
    def __init__(self):
        load_dotenv()
        self.ldap_server = os.getenv("LDAP_SERVER_URL")
        self.ldap_bind_dn = os.getenv("LDAP_BIND_DN")
        self.ldap_bind_password = os.getenv("LDAP_BIND_PASSWORD")
        self.ldap_base_dn = os.getenv("LDAP_BASE_DN")
        self.discord_bot_token = os.getenv("DISCORD_BOT_TOKEN")
        self.lldap_login_url = os.getenv("LLDAP_LOGIN_URL")
        self.subscriber_role_name = os.getenv("SUBSCRIBER_ROLE_NAME")
        self.subscribers_group_id = int(os.getenv("SUBSCRIBERS_GROUP_ID"))
        self.service_name = os.getenv("SERVICE_NAME")  # Default to "Slothflix" if not set

    def get_ldap_username(self):
        """Extracts the username from LDAP_BIND_DN (e.g., 'uid=admin,ou=people,dc=example,dc=com' → 'admin')."""
        if not self.ldap_bind_dn:
            raise ValueError("LDAP_BIND_DN is not set in .env file.")
        # Split by commas and extract the 'uid' part
        parts = self.ldap_bind_dn.split(",")
        for part in parts:
            if part.startswith("uid="):
                return part.split("=")[1]
        raise ValueError("Could not extract username from LDAP_BIND_DN.")