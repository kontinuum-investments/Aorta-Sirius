import datetime

from sirius.communication import discord
from sirius.communication.discord import TextChannel, AortaTextChannels


class Logger:

    @staticmethod
    async def _send_message(text_channel_enum: AortaTextChannels, message: str) -> None:
        text_channel: TextChannel = await TextChannel.get_text_channel_from_default_bot_and_server(text_channel_enum.value)
        await text_channel.send_message(f"{discord.get_timestamp_string(datetime.datetime.now())}: {message}")

    @staticmethod
    async def notify(message: str) -> None:
        await Logger._send_message(AortaTextChannels.NOTIFICATION, message)

    @staticmethod
    async def debug(message: str) -> None:
        await Logger._send_message(AortaTextChannels.DEBUG, message)
