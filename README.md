# LLDAP-Discord

A Discord bot that integrates with GraphQL and LDAP to manage monthly subscribers by adding and removing their access to an LDAP group.
Designed for and tested using the [Lightweight LDAP Project](https://github.com/lldap/lldap)

## Features
- **Automated Subscription Management**: Grants and revokes access based on the subscriber role.
- **Self-Service Account Creation**: Users can register their own LLDAP accounts via a simple Discord command.
- **Admin Controls**: Sync subscribers manually when needed.
- **Designed for Media Servers**: Compatible with Emby and Jellyfin authentication via LDAP.

## Environment Configuration
To configure the bot, create a `.env` file with the following variables:

```ini
DISCORD_BOT_TOKEN=DISCORDTOKEN
LDAP_SERVER_URL=ldap://yoursite.com:3890
LDAP_BIND_DN=uid=admin,ou=people,dc=example,dc=com
LDAP_BIND_PASSWORD=PASSWORD
LDAP_BASE_DN=dc=example,dc=com
LLDAP_LOGIN_URL=https://YourLLDAPWebPage.com
SUBSCRIBER_ROLE_NAME=Subscriber
SUBSCRIBERS_GROUP_ID=4
LIFETIME_ROLE_NAME=Lifetime
LIFETIME_GROUP_ID=5
SERVICE_NAME=YourServiceName
```

## Important Notes
This bot **does not** handle role subscription management. You must use a separate subscription/payment service such as [Upgrade.Chat](https://upgrade.chat/). The bot operates on the assumption that users are already assigned the subscriber role.

Once assigned, users can register an LLDAP account using the `/register` command. They will receive a temporary password and a link to update it via a private message:

![Register Command](https://i.imgur.com/FjPqHJT.png)

![Reply Example](https://i.imgur.com/ZI5xMyo.png)

## Available Commands

### User Commands
#### Register as a Subscriber
```sh
/register <email> [username] (optional)
```
Allows users with the subscriber role to create an LLDAP account.

### Admin Commands
#### Manually Sync Subscribers
```sh
/sync_subscribers
```
Forces a synchronization process in case of any discrepancies.

## Integration with Media Servers
This bot was developed to enable subscription-based access to **Emby** and **Jellyfin**. Below are the required LDAP search filters:

### Jellyfin LDAP Search Filter
```ini
(|(memberof=cn=lifetime,ou=groups,dc=example,dc=com)(memberof=cn=subscribers,ou=groups,dc=example,dc=com))
```

### Emby User Search Filter
```ini
(&(uid={0})(|(memberof=cn=lifetime,ou=groups,dc=example,dc=com)(memberof=cn=subscribers,ou=groups,dc=example,dc=com)))
```

## Updates


### V1.5
- Lifetime Subscriber Role Support
- Custom Username Support
- Shows both discord username and user id in console output


## Support
If this project has helped you, consider supporting me by [buying me a coffee](https://www.buymeacoffee.com/SlothFlix). 🚀

