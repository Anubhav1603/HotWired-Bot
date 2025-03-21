import io
import re
import typing as t

import discord
import requests
from discord.ext.commands import BadArgument, Cog, Context, command
from discord.utils import get

from bot import config
from bot.core.bot import Bot


class InvalidCommandException(Exception):
    pass


class EmoteNotFoundException(Exception):
    pass


class Emote:
    content_re = re.compile(r"^\b(twitch|bttv|ffz)\b\s([\w\d]+)(?:\s(.+))?$", re.I | re.M)

    def __init__(self, emote_type: str, emote_id: str, emote_channel: t.Optional[str]) -> None:
        self.emote_type = emote_type
        self.emote_id = emote_id
        self.emote_channel = emote_channel
        self.name = self.get_name()
        self.image = self.get_image()

    def get_name(self) -> str:
        if self.emote_type == "twitch":
            api_url = "https://api.twitchemotes.com/api/v4/emotes"
            api_res = requests.get(api_url, params={"id": self.emote_id}).json()
            return api_res[0]["code"]

        elif self.emote_type == "frf":
            api_url = f"https://api.frankerfacez.com/v1/emote/{self.emote_id}"
            api_res = requests.get(api_url).json()
            return api_res["emote"]["name"]

        elif self.emote_type == "btv":
            if self.emote_channel == "global":
                api_url = "https://api.betterttv.net/2/emotes"
            else:
                api_url = f"https://api.betterttv.net/2/channels/{self.emote_channel}"

            api_res = requests.get(api_url).json()
            for emote in api_res["emotes"]:
                if emote["id"] == self.emote_id:
                    return emote["code"]

    def get_image(self) -> io.BytesIO:
        img = None
        if self.emote_type == "twitch":
            img = requests.get(f"https://static-cdn.jtvnw.net/emoticons/v1/{self.emote_id}/3.0").content
        elif self.emote_type == "bttv":
            img = requests.get(f"https://cdn.betterttv.net/emote/{self.emote_id}/3x").content
        elif self.emote_type == "ffz":
            img = requests.get(f"https://cdn.frankerfacez.com/emoticon/{self.emote_id}/4").content
        return io.BytesIO(img)

    @classmethod
    def get_emote(cls, content) -> "Emote":
        content_match = re.match(Emote.content_re, content)

        if not content_match:
            raise BadArgument()

        emote_type = content_match[1].lower()
        emote_id = content_match[2].strip().lower()

        emote_channel = None
        if emote_type == "bttv":
            emote_channel = content_match[3]
            if not emote_channel:
                raise BadArgument()
            emote_channel = emote_channel.lower()

        try:
            return cls(emote_type, emote_id, emote_channel)
        except (KeyError, IndexError):
            raise EmoteNotFoundException()


class Emotes(Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    # TODO: Remove this when error handler will be implemented
    async def send_error(self, ctx: Context, error: str) -> None:
        """Sends the Error of Any functions as an Embed."""
        help_message = f"Type `{config.COMMAND_PREFIX}help` for further assistance"
        embed = discord.Embed(colour=discord.Colour.red())
        embed.add_field(name=f"Error: {error}", value=help_message)
        await ctx.send(embed=embed)

    @command()
    async def add_emote(self, ctx: Context, *, content: str) -> None:
        """
        Add an emote to server

        Usage:
            - add_emote twitch <emote_id>
            - add_emote btv <emote_id> <channel_name>
            - add_emote frf <emote_id>

        To get an emote visit:
            - https://twitchemotes.com
            - https://betterttv.com/emotes/shared
            - https://www.frankerfacez.com/emoticons/
        and find an emote you like!.

        The channel name for BetterTTV emotes is found in the top right section of the web page for the emote
        The the ID of the emote is found at the end of the URL for a specific emote.
        - twitchemotes.com/emotes/120232
        - betterttv.com/emotes/5771aa498bbc1e572cb7ae4d
        - frankerfacez.com/emoticon/261802-4Town
        """
        try:
            emote = Emote.get_emote(content)
        except BadArgument:
            await self.send_error(ctx, "Invalid argument")
            return
        except EmoteNotFoundException:
            await self.send_error(ctx, "Emote not found")
            return

        await ctx.guild.create_custom_emoji(name=emote.name, image=emote.image.read())
        discord_emote = get(ctx.guild.emojis, name=emote.name)
        emote_string = f"<:{discord_emote.name}:{discord_emote.id}>"
        if discord_emote.animated:
            emote_string = f"<a:{discord_emote.name}:{discord_emote.id}>"
        await ctx.send(emote_string)

    @command()
    async def emote(self, ctx: Context, *, content: str) -> None:
        """
        Send an emote.

        Supply emote names as a comma-separated list to send multiple emotes in a single message
        """
        names = content.split(",")

        emote_string = ""
        for name in names:
            emote = get(ctx.guild.emojis, name=name)
            if not emote:
                await self.send_error(ctx, f"Emote {name} not found")
                return
            if emote.animated:
                emote_string += f"<a:{emote.name}:{emote.id}>"
            else:
                emote_string += f"<:{emote.name}:{emote.id}>"

        await ctx.send(emote_string)
        await ctx.message.delete()


def setup(bot: Bot) -> None:
    bot.add_cog(Emotes(bot))
