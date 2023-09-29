BASE_URL: str = "https://discord.com/api/"
VERSION_NUMBER: str = "v10"
URL: str = f"{BASE_URL}/{VERSION_NUMBER}/"

#   TODO: Change <> to $
ENDPOINT__BOT__GET_BOT: str = f"{URL}/users/@me"
ENDPOINT__SERVER__GET_ALL_SERVERS: str = f"{URL}/users/@me/guilds"
ENDPOINT__SERVER__GET_ALL_USERS: str = f"{URL}/guilds/$serverID/members"
ENDPOINT__SERVER__GET_ALL_ROLES: str = f"{URL}/guilds/$serverID/roles"
ENDPOINT__CHANNEL__CREATE_CHANNEL_OR_GET_ALL_CHANNELS: str = f"{URL}/guilds/<Server_ID>/channels"
ENDPOINT__CHANNEL__SEND_MESSAGE: str = f"{URL}/channels/<Channel_ID>/messages"
ENDPOINT__CHANNEL__DELETE: str = f"{URL}/channels/$channelID"
