import aiohttp
import asyncio
from datetime import datetime, timedelta

class AuthManager:
    """Handles LLDAP authentication and token management."""
    
    def __init__(self, login_url, username, password):
        self.login_url = login_url
        self.username = username
        self.password = password
        self.jwt_token = None
        self.refresh_token = None
        self.jwt_expiry = None
        self.session = None

    async def initialize(self):
        """Initializes the aiohttp session and authenticates."""
        self.session = aiohttp.ClientSession()
        await self.authenticate()

    async def authenticate(self):
        """Authenticates with LLDAP and obtains JWT and refresh tokens."""
        url = f"{self.login_url}/auth/simple/login"
        payload = {"username": self.username, "password": self.password}
        try:
            async with self.session.post(url, json=payload) as response:
                if response.status != 200:
                    raise Exception(f"Authentication failed: {response.status} {await response.text()}")
                data = await response.json()
                self.jwt_token = data["token"]
                self.refresh_token = data["refreshToken"]
                self.jwt_expiry = datetime.now() + timedelta(days=1)  # JWT valid for 1 day
                print("✅ Successfully authenticated with LLDAP.")
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            raise

    async def refresh(self):
        """Refreshes the JWT token using the refresh token."""
        url = f"{self.login_url}/auth/refresh"
        headers = {"Authorization": f"Bearer {self.refresh_token}"}
        try:
            async with self.session.post(url, headers=headers) as response:
                if response.status != 200:
                    raise Exception(f"Token refresh failed: {response.status} {await response.text()}")
                data = await response.json()
                self.jwt_token = data["token"]
                self.jwt_expiry = datetime.now() + timedelta(days=1)
                print("✅ Successfully refreshed JWT token.")
        except Exception as e:
            print(f"❌ Token refresh error: {e}")
            await self.authenticate()  # Re-authenticate if refresh fails

    async def get_jwt_token(self):
        """Returns the current JWT token, refreshing if expired."""
        if not self.jwt_token or datetime.now() >= self.jwt_expiry:
            await self.refresh()
        return self.jwt_token

    async def close(self):
        """Closes the aiohttp session."""
        if self.session:
            await self.session.close()