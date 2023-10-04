import datetime

from sirius.communication import discord
from sirius.communication.discord import TextChannel, AortaTextChannels, DiscordDefaults


class Logger:

    @staticmethod
    async def _send_message(text_channel_enum: AortaTextChannels, message: str) -> None:
        await DiscordDefaults.send_message(text_channel_enum.value, f"{discord.get_timestamp_string(datetime.datetime.now())}: {message}")

    @staticmethod
    async def notify(message: str) -> None:
        await Logger._send_message(AortaTextChannels.NOTIFICATION, message)

    @staticmethod
    async def debug(message: str) -> None:
        await Logger._send_message(AortaTextChannels.DEBUG, message)
