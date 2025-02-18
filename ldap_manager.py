from ldap3 import Server, Connection, ALL, MODIFY_REPLACE

class LDAPManager:
    """Handles LDAP operations, such as setting user passwords."""
    
    def __init__(self, server_url, bind_dn, bind_password):
        self.server_url = server_url
        self.bind_dn = bind_dn
        self.bind_password = bind_password

    def set_password(self, user_dn, new_password):
        """Sets the LDAP password for a user."""
        try:
            server = Server(self.server_url, get_info=ALL)
            conn = Connection(server, self.bind_dn, self.bind_password, auto_bind=True)

            conn.modify(user_dn, {'userPassword': [(MODIFY_REPLACE, [new_password])]})

            if conn.result['description'] == 'success':
                print(f"✅ Password set successfully for {user_dn}")
                return True
            else:
                print(f"❌ Failed to set password for {user_dn}: {conn.result['message']}")
                return False

        except Exception as e:
            print(f"❌ LDAP Error: {e}")
            return False