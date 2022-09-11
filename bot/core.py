import logging
import textwrap
from typing import Optional, Literal

import discord
from discord import app_commands, Interaction
from discord.ext import commands
from discord.ext.commands import Context, Greedy

log = logging.getLogger(__name__)

class CoreCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name='help', description="See the commands that this bot has to offer")
    async def help_cmd(self, itx: Interaction):
        title = "Bot Help Commands"

        description = textwrap.dedent(
            """For further help, use /cmd and see the hints that discord provides

            **Available Commands**
            /add-channel -- Adds a channel to auto-post pictures to every 4 hours
            /remove-channel -- Removes a channel from auto-posting of pictures
            /random -- Displays a random image to the channel
          
        """)
        embed = discord.Embed(title=title, description=description)

        await itx.response.send_message(embed=embed, ephemeral=True)

    @commands.is_owner()
    @commands.guild_only()
    @commands.command()
    async def sync(self,
            ctx: Context, guilds: Greedy[discord.Object], spec: Optional[Literal["~", "*", "^"]] = None) -> None:
        if not guilds:
            if spec == "~":
                synced = await ctx.bot.tree.sync(guild=ctx.guild)
            elif spec == "*":
                ctx.bot.tree.copy_global_to(guild=ctx.guild)
                synced = await ctx.bot.tree.sync(guild=ctx.guild)
            elif spec == "^":
                ctx.bot.tree.clear_commands(guild=ctx.guild)
                await ctx.bot.tree.sync(guild=ctx.guild)
                synced = []
            else:
                synced = await ctx.bot.tree.sync()

            await ctx.send(
                f"Synced {len(synced)} commands {'globally' if spec is None else 'to the current guild.'}"
            )
            return
        ret = 0
        for guild in guilds:
            try:
                await ctx.bot.tree.sync(guild=guild)
            except discord.HTTPException:
                pass
            else:
                ret += 1
        await ctx.send(f"Synced the tree to {ret}/{len(guilds)}.")


async def setup(bot: commands.Bot):
    await bot.add_cog(CoreCog(bot))