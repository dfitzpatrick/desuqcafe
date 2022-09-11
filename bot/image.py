import io
import logging
import os
import pathlib
import random
from dataclasses import dataclass
from typing import List

import discord
from discord import app_commands
from discord.ext import commands
from discord.ext import tasks

from .config import ConfigMixin

log = logging.getLogger(__name__)

IMAGE_TYPES = ('*.png', '*.jpg', '*.jpeg', '*.webp', '*.gif')
@dataclass
class File:
    path: pathlib.Path
    content: io.BytesIO


def get_file(file_path: pathlib.Path) -> File:
    with file_path.open(mode='rb') as f:
        file_bytes = io.BytesIO(f.read())
        file_bytes.seek(0)
        return File(path=file_path, content=file_bytes)


def random_image(path: pathlib.Path) -> File:
    images = []
    for it in IMAGE_TYPES:
        images.extend(list(path.glob(it)))
    img_path = random.choice(images)
    return get_file(img_path)


def discord_file(file: File) -> discord.File:
    return discord.File(file.content, filename=file.path.name)


class ImageCog(ConfigMixin, commands.Cog):
    def __init__(self, bot: commands.Bot, image_path: pathlib.Path):
        self.bot = bot
        self.image_path = image_path
        super().__init__()
        self.image_task.start()

    def get_random_discord_image(self) -> File:
        return random_image(self.image_path)

    async def send_image_to_channels(self, image: File, guild_id: str, channel_ids: List[int]):
        guild_id = int(guild_id)
        guild = self.bot.get_guild(guild_id)
        if guild is None:
            return
        for channel_id in channel_ids:
            channel = guild.get_channel(channel_id)
            if channel is None:
                continue
            try:
                image.content.seek(0)
                await channel.send(file=discord.File(image.content, filename=image.path.name))
            except (PermissionError, discord.HTTPException):
                log.error(f"{guild.id}/{guild.name} Could not send to channel {channel.name} No Permissions/HTTPException")
                continue

    @app_commands.command(name='random')
    async def random_image(self, itx: discord.Interaction):
        img = self.get_random_discord_image()
        await self.send_image_to_channels(img, str(itx.guild_id), [itx.channel_id])
        await itx.response.send_message("A random image!", ephemeral=True)

    @app_commands.checks.has_permissions(manage_channels=True)
    @app_commands.command(name='add-channel')
    async def add_channel(self, itx: discord.Interaction, channel: discord.TextChannel = None):
        key = str(itx.guild_id)
        channel_id = channel.id if channel is not None else itx.channel_id
        if key not in self.config_settings.keys():
            self.config_settings[key] = []
        if channel_id not in self.config_settings[key]:
            self.config_settings[key].append(channel_id)
        self.save_settings()
        await itx.response.send_message("Channel Added", ephemeral=True)

    @app_commands.checks.has_permissions(manage_channels=True)
    @app_commands.command(name='remove-channel')
    async def remove_channel(self, itx: discord.Interaction, channel: discord.TextChannel = None):
        key = str(itx.guild_id)
        channel_id = channel.id if channel is not None else itx.channel_id
        if key not in self.config_settings.keys():
            self.config_settings[key] = []
        else:
            try:
                self.config_settings[key].remove(channel_id)
            except ValueError:
                pass
        self.save_settings()
        await itx.response.send_message("Channel Removed", ephemeral=True)


    @tasks.loop(hours=4, reconnect=True)
    async def image_task(self):
        img = self.get_random_discord_image()
        for guild_str, channels in self.config_settings.items():
            await self.send_image_to_channels(img, guild_str, channels)

    @image_task.before_loop
    async def before_image_task(self):
        await self.bot.wait_until_ready()
        log.info("Image task started")


async def setup(bot):
    path = os.environ.get('IMAGE_DIR')
    assert path is not None, "The Environment Variable 'IMAGE_DIR' could not be found and is required!"
    path = pathlib.Path(path)
    assert path.exists(), f"The 'IMAGE_DIR' ({path}) is not a valid directory"
    await bot.add_cog(ImageCog(bot, path))


